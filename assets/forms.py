from pathlib import Path

from django import forms

from .models import (
    AssetDocument,
    Block,
    Component,
    Drawing,
    DynamicQRCode,
    ExcelImportBatch,
    Level,
    MaintenanceRequest,
    Premise,
    Room,
    RoomFunctionCode,
)


class PremiseForm(forms.ModelForm):
    class Meta:
        model = Premise

        fields = [
            "name",
            "dpa_number",
            "address",
            "ministry",
            "department",
            "state",
            "district",
            "status",
        ]


class BlockForm(forms.ModelForm):
    class Meta:
        model = Block

        fields = [
            "premise",
            "structure_type",
            "security_level",
            "code",
            "name",
            "function",
            "status",
        ]


class LevelForm(forms.ModelForm):
    class Meta:
        model = Level

        fields = [
            "block",
            "code",
            "name",
            "sequence",
        ]


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room

        fields = [
            "level",
            "space_type",
            "security_level",
            "code",
            "name",
            "room_function",
            "area",
        ]

        widgets = {
            "level": forms.Select(
                attrs={"class": "form-control"}
            ),
            "space_type": forms.Select(
                attrs={"class": "form-control"}
            ),
            "security_level": forms.Select(
                attrs={"class": "form-control"}
            ),
            "code": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "room_function": forms.Select(
                attrs={"class": "form-control"}
            ),
            "area": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["room_function"].queryset = (
            RoomFunctionCode.objects.filter(
                is_active=True
            ).order_by("code")
        )

        self.fields["room_function"].required = False

        self.fields["room_function"].empty_label = (
            "Select Room Function Code"
        )

    def save(self, commit=True):
        room = super().save(commit=False)

        if room.room_function:
            room.function_code = room.room_function.code
            room.function_name = room.room_function.name

        if commit:
            room.save()

        return room


class ComponentForm(forms.ModelForm):
    class Meta:
        model = Component

        fields = [
            "room",
            "component_id",
            "name",
            "component_code",
            "discipline",
            "system",
            "subsystem",
            "brand",
            "model",
            "serial_number",
            "installation_date",
            "warranty_expiry",
            "security_level",
            "status",
        ]

        widgets = {
            "installation_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "warranty_expiry": forms.DateInput(
                attrs={"type": "date"}
            ),
        }


class DynamicQRCodeForm(forms.ModelForm):

    class Meta:
        model = DynamicQRCode

        fields = (
            "qr_type",
            "premise",
            "block",
            "level",
            "room",
            "component",
            "is_active",
        )

        widgets = {

            "qr_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "premise": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "block": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "level": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "room": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "component": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox",
                }
            ),
        }


    def clean(self):

        cleaned_data = super().clean()

        qr_type = cleaned_data.get(
            "qr_type"
        )


        targets = {

            "premise": (
                cleaned_data.get(
                    "premise"
                )
            ),

            "block": (
                cleaned_data.get(
                    "block"
                )
            ),

            "level": (
                cleaned_data.get(
                    "level"
                )
            ),

            "room": (
                cleaned_data.get(
                    "room"
                )
            ),

            "component": (
                cleaned_data.get(
                    "component"
                )
            ),
        }


        selected_targets = [
            name
            for name, value in targets.items()
            if value is not None
        ]


        if len(selected_targets) != 1:

            raise forms.ValidationError(
                "Select exactly one asset for this QR code."
            )


        if (
            qr_type
            and selected_targets[0] != qr_type
        ):

            raise forms.ValidationError(
                f"QR type is {qr_type}, but the selected asset is "
                f"{selected_targets[0]}."
            )


        return cleaned_data


class QRReplacementForm(forms.Form):

    new_qr_id = forms.CharField(
        max_length=100,
        label="New QR ID",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: QR001-R2",
            }
        ),
    )


    replacement_reason = forms.CharField(
        max_length=255,
        label="Replacement Reason",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": (
                    "Example: Existing label damaged or unreadable"
                ),
            }
        ),
    )


    def clean_new_qr_id(self):

        new_qr_id = (
            self.cleaned_data["new_qr_id"]
            .strip()
        )


        if DynamicQRCode.objects.filter(
            qr_id=new_qr_id
        ).exists():

            raise forms.ValidationError(
                "A QR code with this ID already exists."
            )


        return new_qr_id


class DrawingForm(forms.ModelForm):
    class Meta:
        model = Drawing

        fields = (
            "premise",
            "block",
            "level",
            "room",
            "component",
            "drawing_number",
            "title",
            "drawing_type",
            "revision",
            "drawing_date",
            "file",
            "description",
            "status",
        )

        widgets = {
            "premise": forms.Select(
                attrs={"class": "form-control"}
            ),
            "block": forms.Select(
                attrs={"class": "form-control"}
            ),
            "level": forms.Select(
                attrs={"class": "form-control"}
            ),
            "room": forms.Select(
                attrs={"class": "form-control"}
            ),
            "component": forms.Select(
                attrs={"class": "form-control"}
            ),
            "drawing_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: ARCH-B01-001",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Ground Floor Plan",
                }
            ),
            "drawing_type": forms.Select(
                attrs={"class": "form-control"}
            ),
            "revision": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 0, A or R1",
                }
            ),
            "drawing_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".pdf,.dwg,.dxf,.jpg,.jpeg,.png"
                    ),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "status": forms.Select(
                attrs={"class": "form-control"}
            ),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return uploaded_file

        allowed_extensions = {
            ".pdf",
            ".dwg",
            ".dxf",
            ".jpg",
            ".jpeg",
            ".png",
        }

        extension = Path(
            uploaded_file.name
        ).suffix.lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                "Upload a PDF, DWG, DXF, JPG, JPEG or PNG file."
            )

        maximum_size = 20 * 1024 * 1024

        if uploaded_file.size > maximum_size:
            raise forms.ValidationError(
                "The drawing file must not exceed 20 MB."
            )

        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()

        premise = cleaned_data.get("premise")
        block = cleaned_data.get("block")
        level = cleaned_data.get("level")
        room = cleaned_data.get("room")
        component = cleaned_data.get("component")

        if block and premise:
            if block.premise_id != premise.id:
                self.add_error(
                    "block",
                    (
                        "The selected block does not belong "
                        "to this premise."
                    ),
                )

        if level and block:
            if level.block_id != block.id:
                self.add_error(
                    "level",
                    (
                        "The selected level does not belong "
                        "to this block."
                    ),
                )

        if room and level:
            if room.level_id != level.id:
                self.add_error(
                    "room",
                    (
                        "The selected room does not belong "
                        "to this level."
                    ),
                )

        if component and room:
            if component.room_id != room.id:
                self.add_error(
                    "component",
                    (
                        "The selected component does not belong "
                        "to this room."
                    ),
                )

        return cleaned_data

class AssetDocumentForm(forms.ModelForm):
    class Meta:
        model = AssetDocument

        fields = (
            "premise",
            "block",
            "level",
            "room",
            "component",
            "document_number",
            "title",
            "document_type",
            "issue_date",
            "expiry_date",
            "file",
            "description",
            "status",
        )

        widgets = {
            "premise": forms.Select(
                attrs={"class": "form-control"}
            ),
            "block": forms.Select(
                attrs={"class": "form-control"}
            ),
            "level": forms.Select(
                attrs={"class": "form-control"}
            ),
            "room": forms.Select(
                attrs={"class": "form-control"}
            ),
            "component": forms.Select(
                attrs={"class": "form-control"}
            ),
            "document_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: DOC-001",
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Air Conditioner Manual",
                }
            ),
            "document_type": forms.Select(
                attrs={"class": "form-control"}
            ),
            "issue_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".pdf,.doc,.docx,.xls,.xlsx,"
                        ".jpg,.jpeg,.png"
                    ),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "status": forms.Select(
                attrs={"class": "form-control"}
            ),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return uploaded_file

        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".jpg",
            ".jpeg",
            ".png",
        }

        extension = Path(
            uploaded_file.name
        ).suffix.lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                "Upload a PDF, Word, Excel, JPG, JPEG "
                "or PNG file."
            )

        maximum_size = 20 * 1024 * 1024

        if uploaded_file.size > maximum_size:
            raise forms.ValidationError(
                "The document file must not exceed 20 MB."
            )

        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()

        premise = cleaned_data.get("premise")
        block = cleaned_data.get("block")
        level = cleaned_data.get("level")
        room = cleaned_data.get("room")
        component = cleaned_data.get("component")
        issue_date = cleaned_data.get("issue_date")
        expiry_date = cleaned_data.get("expiry_date")

        if block and premise:
            if block.premise_id != premise.id:
                self.add_error(
                    "block",
                    "The selected block does not belong "
                    "to this premise.",
                )

        if level and block:
            if level.block_id != block.id:
                self.add_error(
                    "level",
                    "The selected level does not belong "
                    "to this block.",
                )

        if room and level:
            if room.level_id != level.id:
                self.add_error(
                    "room",
                    "The selected room does not belong "
                    "to this level.",
                )

        if component and room:
            if component.room_id != room.id:
                self.add_error(
                    "component",
                    "The selected component does not belong "
                    "to this room.",
                )

        if issue_date and expiry_date:
            if expiry_date < issue_date:
                self.add_error(
                    "expiry_date",
                    "The expiry date cannot be earlier "
                    "than the issue date.",
                )

        return cleaned_data

class ExcelImportBatchForm(forms.ModelForm):

    class Meta:
        model = ExcelImportBatch

        # The new DA6 workflow only requires
        # the workbook.
        #
        # Premise will be detected automatically
        # from the DPA Number inside the workbook.
        #
        # import_type will use the model default:
        # "full_da6"
        fields = (
            "file",
        )

        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".xlsx,.xlsm",
                }
            ),
        }


    def clean_file(self):

        uploaded_file = (
            self.cleaned_data.get(
                "file"
            )
        )

        if not uploaded_file:
            return uploaded_file


        # =========================================
        # FILE EXTENSION
        # =========================================

        extension = Path(
            uploaded_file.name
        ).suffix.lower()


        if extension not in {
            ".xlsx",
            ".xlsm",
        }:

            raise forms.ValidationError(
                (
                    "Please upload a DA6 Excel "
                    ".xlsx or .xlsm file."
                )
            )


        # =========================================
        # FILE SIZE
        # =========================================

        maximum_size = (
            20 * 1024 * 1024
        )


        if (
            uploaded_file.size
            > maximum_size
        ):

            raise forms.ValidationError(
                (
                    "The DA6 Excel file must "
                    "not exceed 20 MB."
                )
            )


        return uploaded_file

class MaintenanceRequestForm(forms.ModelForm):

    class Meta:
        model = MaintenanceRequest

        fields = (
            "premise",
            "block",
            "level",
            "room",
            "component",
            "category",
            "description",
            "priority",
            "reporter_name",
            "reporter_contact",
        )

        widgets = {
            "premise": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_premise",
                }
            ),

            "block": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_block",
                }
            ),

            "level": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_level",
                }
            ),

            "room": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_room",
                }
            ),

            "component": forms.Select(
                attrs={
                    "class": "form-control",
                    "id": "id_component",
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe the maintenance issue "
                        "or complaint."
                    ),
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "reporter_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Reporter name",
                }
            ),

            "reporter_contact": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Contact number",
                }
            ),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Premise is always available.
        self.fields["premise"].queryset = (
            Premise.objects.all()
            .order_by("name")
        )

        # Start dependent fields empty.
        self.fields["block"].queryset = (
            Block.objects.none()
        )

        self.fields["level"].queryset = (
            Level.objects.none()
        )

        self.fields["room"].queryset = (
            Room.objects.none()
        )

        self.fields["component"].queryset = (
            Component.objects.none()
        )

        self.fields["block"].required = False
        self.fields["level"].required = False
        self.fields["room"].required = False
        self.fields["component"].required = False

        self.fields["block"].empty_label = (
            "Select Block"
        )

        self.fields["level"].empty_label = (
            "Select Level"
        )

        self.fields["room"].empty_label = (
            "Select Room / Open Area"
        )

        self.fields["component"].empty_label = (
            "Select Component (Optional)"
        )


        # =========================================
        # POSTED FORM DATA
        # =========================================

        if "premise" in self.data:

            try:
                premise_id = int(
                    self.data.get("premise")
                )

                self.fields["block"].queryset = (
                    Block.objects.filter(
                        premise_id=premise_id
                    )
                    .order_by("code")
                )

            except (
                TypeError,
                ValueError,
            ):
                pass


        if "block" in self.data:

            try:
                block_id = int(
                    self.data.get("block")
                )

                self.fields["level"].queryset = (
                    Level.objects.filter(
                        block_id=block_id
                    )
                    .order_by(
                        "sequence",
                        "code",
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                pass


        if "level" in self.data:

            try:
                level_id = int(
                    self.data.get("level")
                )

                self.fields["room"].queryset = (
                    Room.objects.filter(
                        level_id=level_id
                    )
                    .order_by("code")
                )

            except (
                TypeError,
                ValueError,
            ):
                pass


        if "room" in self.data:

            try:
                room_id = int(
                    self.data.get("room")
                )

                self.fields[
                    "component"
                ].queryset = (
                    Component.objects.filter(
                        room_id=room_id
                    )
                    .order_by("name")
                )

            except (
                TypeError,
                ValueError,
            ):
                pass


        # =========================================
        # EXISTING RECORD
        # =========================================

        elif self.instance.pk:

            if self.instance.premise_id:
                self.fields["block"].queryset = (
                    Block.objects.filter(
                        premise=(
                            self.instance.premise
                        )
                    )
                    .order_by("code")
                )

            if self.instance.block_id:
                self.fields["level"].queryset = (
                    Level.objects.filter(
                        block=(
                            self.instance.block
                        )
                    )
                    .order_by(
                        "sequence",
                        "code",
                    )
                )

            if self.instance.level_id:
                self.fields["room"].queryset = (
                    Room.objects.filter(
                        level=(
                            self.instance.level
                        )
                    )
                    .order_by("code")
                )

            if self.instance.room_id:
                self.fields[
                    "component"
                ].queryset = (
                    Component.objects.filter(
                        room=(
                            self.instance.room
                        )
                    )
                    .order_by("name")
                )


    def clean(self):
        cleaned_data = super().clean()

        premise = cleaned_data.get(
            "premise"
        )

        block = cleaned_data.get(
            "block"
        )

        level = cleaned_data.get(
            "level"
        )

        room = cleaned_data.get(
            "room"
        )

        component = cleaned_data.get(
            "component"
        )


        if block and premise:

            if (
                block.premise_id
                != premise.id
            ):
                self.add_error(
                    "block",
                    (
                        "The selected block does "
                        "not belong to this premise."
                    ),
                )


        if level and block:

            if (
                level.block_id
                != block.id
            ):
                self.add_error(
                    "level",
                    (
                        "The selected level does "
                        "not belong to this block."
                    ),
                )


        if room and level:

            if (
                room.level_id
                != level.id
            ):
                self.add_error(
                    "room",
                    (
                        "The selected room does "
                        "not belong to this level."
                    ),
                )


        if component and room:

            if (
                component.room_id
                != room.id
            ):
                self.add_error(
                    "component",
                    (
                        "The selected component "
                        "does not belong to this room."
                    ),
                )


        return cleaned_data