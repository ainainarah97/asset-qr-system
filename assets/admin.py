from django.contrib import admin

from .models import (
    AssetDocument,
    Block,
    Component,
    Drawing,
    DynamicQRCode,
    ExcelImportBatch,
    Level,
    Premise,
    Room,
    RoomFunctionCode,
    MaintenanceRequest,
)


@admin.register(Premise)
class PremiseAdmin(admin.ModelAdmin):
    list_display = (
        "dpa_number",
        "name",
        "ministry",
        "department",
        "state",
        "district",
        "status",
    )

    list_filter = (
        "state",
        "district",
        "status",
    )

    search_fields = (
        "dpa_number",
        "name",
        "ministry",
        "department",
        "address",
    )

    ordering = (
        "name",
    )


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "premise",
        "structure_type",
        "security_level",
        "status",
    )

    list_filter = (
        "structure_type",
        "security_level",
        "status",
        "premise",
    )

    search_fields = (
        "code",
        "name",
        "function",
        "premise__name",
        "premise__dpa_number",
    )

    ordering = (
        "premise",
        "code",
    )


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "block",
        "sequence",
    )

    list_filter = (
        "block",
        "block__premise",
    )

    search_fields = (
        "code",
        "name",
        "block__code",
        "block__name",
        "block__premise__name",
    )

    ordering = (
        "block",
        "sequence",
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "level",
        "space_type",
        "function_code",
        "function_name",
        "security_level",
        "area",
    )

    list_filter = (
        "space_type",
        "security_level",
        "level",
        "level__block",
    )

    search_fields = (
        "code",
        "name",
        "function_code",
        "function_name",
        "room_tag",
        "level__name",
        "level__block__name",
        "level__block__premise__name",
    )

    ordering = (
        "level",
        "code",
    )


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = (
        "component_id",
        "name",
        "component_code",
        "room",
        "discipline",
        "system",
        "brand",
        "model",
        "status",
    )

    list_filter = (
        "discipline",
        "system",
        "security_level",
        "status",
        "room",
    )

    search_fields = (
        "component_id",
        "name",
        "component_code",
        "serial_number",
        "brand",
        "model",
        "room__name",
        "room__room_tag",
    )

    ordering = (
        "component_id",
    )


@admin.register(DynamicQRCode)
class DynamicQRCodeAdmin(admin.ModelAdmin):
    list_display = (
        "qr_id",
        "qr_type",
        "is_active",
        "scan_count",
        "last_scan",
        "created_at",
    )

    list_filter = (
        "qr_type",
        "is_active",
    )

    search_fields = (
        "qr_id",
        "premise__name",
        "block__name",
        "level__name",
        "room__name",
        "component__name",
        "component__component_id",
    )

    readonly_fields = (
        "public_id",
        "scan_count",
        "last_scan",
        "deactivated_at",
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Drawing)
class DrawingAdmin(admin.ModelAdmin):
    list_display = (
        "drawing_number",
        "title",
        "drawing_type",
        "revision",
        "premise",
        "status",
        "uploaded_by",
        "created_at",
    )

    list_filter = (
        "drawing_type",
        "status",
        "premise",
    )

    search_fields = (
        "drawing_number",
        "title",
        "description",
        "premise__name",
        "block__name",
        "level__name",
        "room__name",
        "component__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "drawing_number",
        "-revision",
    )


@admin.register(AssetDocument)
class AssetDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "document_number",
        "title",
        "document_type",
        "premise",
        "status",
        "issue_date",
        "expiry_date",
        "uploaded_by",
        "created_at",
    )

    list_filter = (
        "document_type",
        "status",
        "premise",
    )

    search_fields = (
        "document_number",
        "title",
        "description",
        "premise__name",
        "block__name",
        "level__name",
        "room__name",
        "component__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "document_number",
    )


@admin.register(RoomFunctionCode)
class RoomFunctionCodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "category",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "category",
        "description",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "code",
    )

@admin.register(ExcelImportBatch)
class ExcelImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "import_type",
        "status",
        "total_rows",
        "successful_rows",
        "failed_rows",
        "uploaded_by",
        "created_at",
    )

    list_filter = (
        "import_type",
        "status",
        "created_at",
    )

    search_fields = (
        "file",
        "error_log",
        "uploaded_by__username",
    )

    readonly_fields = (
        "total_rows",
        "successful_rows",
        "failed_rows",
        "error_log",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):

    list_display = (
        "request_no",
        "category",
        "priority",
        "status",
        "premise",
        "room",
        "component",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "category",
    )

    search_fields = (
        "request_no",
        "description",
        "component__name",
        "room__name",
        "premise__name",
    )

    readonly_fields = (
        "request_no",
        "created_at",
        "updated_at",
    )