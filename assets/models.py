import uuid
from django.db import models
from django.conf import settings

class Premise(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]


    LABEL_STATUS_CHOICES = [
        ("draft", "Draft"),
        ("prepared", "Prepared"),
        ("installed", "Installed"),
        ("verified", "Verified"),
    ]


    VERIFICATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]



    name = models.CharField(
        max_length=250,
    )


    dpa_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
    )


    address = models.TextField()



    ministry = models.CharField(
        max_length=200,
        blank=True,
    )


    department = models.CharField(
        max_length=200,
        blank=True,
    )


    state = models.CharField(
        max_length=100,
    )


    district = models.CharField(
        max_length=100,
        blank=True,
    )



    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )



    owner_agency = models.CharField(
        max_length=200,
        blank=True,
    )


    jkr_reference = models.CharField(
        max_length=200,
        blank=True,
    )



    qr_enabled = models.BooleanField(
        default=True,
    )



    label_size = models.CharField(
        max_length=100,
        default="600mm x 400mm",
    )



    label_material = models.CharField(
        max_length=200,
        default="Stainless Steel 304 Hairline Finish 1.5mm",
    )



    label_status = models.CharField(
        max_length=50,
        choices=LABEL_STATUS_CHOICES,
        default="draft",
    )



    installation_date = models.DateField(
        blank=True,
        null=True,
    )



    installation_photo = models.ImageField(
        upload_to="premise_labels/",
        blank=True,
        null=True,
    )



    verification_status = models.CharField(
        max_length=50,
        choices=VERIFICATION_STATUS_CHOICES,
        default="pending",
    )



    # ==========================================
    # SORTING / RECORD CREATION DATE
    # ==========================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )



    def __str__(self):

        if self.dpa_number:

            return (
                f"{self.name} "
                f"({self.dpa_number})"
            )

        return self.name

class Block(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    STRUCTURE_TYPE_CHOICES = [
        ("building", "Building Block"),
        ("external", "External Structure"),
    ]

    SECURITY_LEVEL_CHOICES = [
        ("public", "Public"),
        ("staff", "Staff Only"),
        ("restricted", "Restricted"),
    ]

    premise = models.ForeignKey(
        Premise,
        on_delete=models.CASCADE,
        related_name="blocks",
    )

    structure_type = models.CharField(
        max_length=20,
        choices=STRUCTURE_TYPE_CHOICES,
        default="building",
    )

    security_level = models.CharField(
        max_length=20,
        choices=SECURITY_LEVEL_CHOICES,
        default="staff",
    )

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=250)
    function = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["premise", "code"],
                name="unique_block_code_per_premise",
            )
        ]
        ordering = ["premise", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

class Level(models.Model):
    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        related_name="levels",
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    sequence = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["block", "code"],
                name="unique_level_code_per_block",
            )
        ]
        ordering = ["block", "sequence", "code"]

    def __str__(self):
        return f"{self.block.code}.{self.code} - {self.name}"

class RoomFunctionCode(models.Model):
    space_type_code = models.CharField(
        max_length=5,
        blank=True,
    )

    space_type_name = models.CharField(
        max_length=255,
        blank=True,
    )

    category_code = models.CharField(
        max_length=20,
        blank=True,
    )

    category = models.CharField(
        max_length=255,
        blank=True,
    )

    code = models.CharField(
        max_length=20,
        unique=True,
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "space_type_code",
            "category_code",
            "code",
        ]

        verbose_name = "Room Function Code"
        verbose_name_plural = "Room Function Codes"

    def __str__(self):
        return f"{self.code} — {self.name}"


class Room(models.Model):

    SPACE_TYPE_CHOICES = [
        ("room", "Enclosed Room"),
        ("open_area", "Open Area"),
    ]

    SECURITY_LEVEL_CHOICES = [
        ("public", "Public"),
        ("staff", "Staff Only"),
        ("restricted", "Restricted"),
    ]

    space_type = models.CharField(
        max_length=20,
        choices=SPACE_TYPE_CHOICES,
        default="room",
    )

    security_level = models.CharField(
        max_length=20,
        choices=SECURITY_LEVEL_CHOICES,
        default="staff",
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        related_name="rooms",
    )

    code = models.CharField(
        max_length=20,
    )

    name = models.CharField(
        max_length=200,
    )

    room_function = models.ForeignKey(
        RoomFunctionCode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rooms",
    )

    function_code = models.CharField(
        max_length=50,
        blank=True,
    )

    function_name = models.CharField(
        max_length=200,
        blank=True,
    )

    area = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    room_tag = models.CharField(
        max_length=100,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["level", "code"],
                name="unique_room_code_per_level",
            )
        ]

        ordering = [
            "level",
            "code",
        ]

    def save(self, *args, **kwargs):
        self.room_tag = (
            f"{self.level.block.code}."
            f"{self.level.code}."
            f"{self.code}"
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.room_tag} - {self.name}"
    
class Component(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("returned", "Returned for Correction"),
        ("verified", "Verified"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    DISCIPLINE_CHOICES = [
        ("A", "Civil and Architecture"),
        ("E", "Electrical"),
        ("M", "Mechanical"),
        ("T", "ICT and ELV"),
        ("B", "Biomedical"),
        ("L", "Other"),
    ]

    SECURITY_LEVEL_CHOICES = [
        ("public", "Public"),
        ("staff", "Staff Only"),
        ("restricted", "Restricted"),
    ]

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="components",
    )
    security_level = models.CharField(
        max_length=20,
        choices=SECURITY_LEVEL_CHOICES,
        default="staff",
    )
    component_id = models.CharField(
        max_length=150,
    )
    name = models.CharField(max_length=250)
    component_code = models.CharField(
        max_length=100,
        blank=True,
    )
    discipline = models.CharField(
        max_length=1,
        choices=DISCIPLINE_CHOICES,
    )
    system = models.CharField(max_length=250)
    subsystem = models.CharField(
        max_length=250,
        blank=True,
    )
    brand = models.CharField(
        max_length=150,
        blank=True,
    )
    model = models.CharField(
        max_length=150,
        blank=True,
    )
    serial_number = models.CharField(
        max_length=200,
        blank=True,
    )
    installation_date = models.DateField(
        null=True,
        blank=True,
    )
    warranty_expiry = models.DateField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "room",
                    "component_id",
                ],
                name="unique_component_per_room",
            )
        ]

    def __str__(self):
        return f"{self.component_id} - {self.name}"

class AssetLabel(models.Model):

    LABEL_TYPE_CHOICES = [
        ("dpa", "DPA Label"),
        ("block", "DAK Block / External Structure"),
        ("level", "DAK Level"),
        ("room", "DAK Room"),
        ("component", "DAK Component"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("printed", "Printed"),
        ("installed", "Installed"),
        ("verified", "Verified"),
    ]


    label_type = models.CharField(
        max_length=30,
        choices=LABEL_TYPE_CHOICES,
    )


    label_code = models.CharField(
        max_length=100,
        unique=True,
    )


    premise = models.ForeignKey(
        Premise,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="labels",
    )


    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="labels",
    )


    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="labels",
    )


    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="labels",
    )


    qr_code = models.CharField(
        max_length=500,
        blank=True,
    )


    label_size = models.CharField(
        max_length=100,
        blank=True,
    )


    material = models.CharField(
        max_length=200,
        blank=True,
    )


    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="draft",
    )


    installation_date = models.DateField(
        null=True,
        blank=True,
    )


    installer = models.CharField(
        max_length=150,
        blank=True,
    )


    installation_photo = models.ImageField(
        upload_to="label_evidence/",
        blank=True,
        null=True,
    )


    verified_by = models.CharField(
        max_length=150,
        blank=True,
    )


    verification_date = models.DateField(
        null=True,
        blank=True,
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return (
            f"{self.label_code} - "
            f"{self.get_label_type_display()}"
        )

class DynamicQRCode(models.Model):

    QR_TYPE_CHOICES = [
        ("premise", "Premise QR"),
        ("block", "Block QR"),
        ("level", "Level QR"),
        ("room", "Room QR"),
        ("component", "Component QR"),
    ]

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    qr_id = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        blank=True,
    )

    qr_type = models.CharField(
        max_length=30,
        choices=QR_TYPE_CHOICES,
    )

    premise = models.ForeignKey(
        Premise,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_codes",
    )

    block = models.ForeignKey(
        Block,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_codes",
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_codes",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_codes",
    )

    component = models.ForeignKey(
        Component,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="qr_codes",
    )

    is_active = models.BooleanField(
        default=True,
    )

    last_scan = models.DateTimeField(
        null=True,
        blank=True,
    )

    scan_count = models.PositiveIntegerField(
        default=0,
    )

    replaced_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )

    replacement_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def save(self, *args, **kwargs):

        if not self.qr_id:
            self.qr_id = str(uuid.uuid4())

        super().save(*args, **kwargs)


    def __str__(self):
        return self.qr_id

class Drawing(models.Model):
    DRAWING_TYPE_CHOICES = [
        ("architectural", "Architectural"),
        ("structural", "Structural"),
        ("civil", "Civil"),
        ("mechanical", "Mechanical"),
        ("electrical", "Electrical"),
        ("as_built", "As-Built"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("current", "Current"),
        ("superseded", "Superseded"),
        ("archived", "Archived"),
    ]

    premise = models.ForeignKey(
        Premise,
        on_delete=models.CASCADE,
        related_name="drawings",
    )

    block = models.ForeignKey(
        Block,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drawings",
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drawings",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drawings",
    )

    component = models.ForeignKey(
        Component,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drawings",
    )

    drawing_number = models.CharField(
        max_length=100,
    )

    title = models.CharField(
        max_length=255,
    )

    drawing_type = models.CharField(
        max_length=30,
        choices=DRAWING_TYPE_CHOICES,
    )

    revision = models.CharField(
        max_length=20,
        default="0",
    )

    drawing_date = models.DateField(
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="drawings/%Y/%m/",
    )

    description = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="current",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_drawings",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "drawing_number",
            "-revision",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "drawing_number",
                    "revision",
                ],
                name="unique_drawing_revision",
            ),
        ]

    def __str__(self):
        return (
            f"{self.drawing_number} - "
            f"{self.title} (Rev {self.revision})"
        )

class AssetDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("manual", "Operation and Maintenance Manual"),
        ("warranty", "Warranty Document"),
        ("certificate", "Certificate"),
        ("inspection", "Inspection Report"),
        ("maintenance", "Maintenance Report"),
        ("handover", "Handover Document"),
        ("contract", "Contract Document"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("current", "Current"),
        ("expired", "Expired"),
        ("archived", "Archived"),
    ]

    premise = models.ForeignKey(
        Premise,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    block = models.ForeignKey(
        Block,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    component = models.ForeignKey(
        Component,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    document_number = models.CharField(
        max_length=100,
        unique=True,
    )

    title = models.CharField(
        max_length=255,
    )

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    file = models.FileField(
        upload_to="documents/%Y/%m/",
    )

    description = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="current",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_asset_documents",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "document_number",
        ]

    def __str__(self):
        return f"{self.document_number} — {self.title}"

class ExcelImportBatch(models.Model):

    premise = models.ForeignKey(
        Premise,
        on_delete=models.PROTECT,
        related_name="excel_import_batches",
        null=True,
        blank=True,
    )

    IMPORT_TYPE_CHOICES = [
        ("full_da6", "Full DA6 Bulk Import"),
        ("rooms", "Rooms & Open Areas"),
        ("components", "Asset Components"),
    ]

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("validated", "Validated"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    import_type = models.CharField(
        max_length=20,
        choices=IMPORT_TYPE_CHOICES,
        default="full_da6",
    )

    import_sheet = models.CharField(
        max_length=100,
        blank=True,
    )

    file = models.FileField(
        upload_to="imports/%Y/%m/",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded",
    )

    total_rows = models.PositiveIntegerField(
        default=0,
    )

    successful_rows = models.PositiveIntegerField(
        default=0,
    )

    failed_rows = models.PositiveIntegerField(
        default=0,
    )

    error_log = models.TextField(
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asset_excel_imports",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.get_import_type_display()} "
            f"— {self.created_at:%d %b %Y %H:%M}"
        )

class MaintenanceRequest(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    CATEGORY_CHOICES = [
        ("civil", "Civil"),
        ("electrical", "Electrical"),
        ("mechanical", "Mechanical"),
        ("ict", "ICT"),
        ("other", "Other"),
    ]


    # ==========================
    # LOCATION HIERARCHY
    # ==========================

    premise = models.ForeignKey(
        Premise,
        on_delete=models.PROTECT,
        related_name="maintenance_requests",
    )

    block = models.ForeignKey(
        Block,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )

    level = models.ForeignKey(
        Level,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )

    component = models.ForeignKey(
        Component,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )

    qr_code = models.ForeignKey(
        "DynamicQRCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )


    # ==========================
    # REQUEST DETAILS
    # ==========================

    request_no = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
    )

    description = models.TextField()


    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted",
    )


    # ==========================
    # REPORTER
    # ==========================

    reported_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_maintenance_requests",
    )

    reporter_name = models.CharField(
        max_length=150,
        blank=True,
    )

    reporter_contact = models.CharField(
        max_length=50,
        blank=True,
    )


    # ==========================
    # MANAGEMENT
    # ==========================

    assigned_to = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_maintenance_requests",
    )


    remarks = models.TextField(
        blank=True,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    def save(self, *args, **kwargs):

        if not self.request_no:
            last_id = (
                MaintenanceRequest.objects.count()
                + 1
            )

            self.request_no = (
                f"MR-{last_id:05d}"
            )

        super().save(*args, **kwargs)


    def __str__(self):
        return (
            f"{self.request_no} - "
            f"{self.description[:40]}"
        )
qr_code = models.ForeignKey(
    DynamicQRCode,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="maintenance_requests",
)
