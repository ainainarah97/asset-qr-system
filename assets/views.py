from io import BytesIO
from pathlib import Path
import re

import qrcode

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)



from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from xml.sax.saxutils import escape

from django.urls import reverse
from django.utils import timezone

from .excel_importer import (
    get_or_create_premise_from_workbook,
    import_da6_blocks,
    import_da6_rooms,
    import_da6_components,
    validate_da6_block_rows,
    validate_full_da6_file,
    validate_room_rows,
    validate_excel_file,
)

from .forms import (
    AssetDocumentForm,
    BlockForm,
    ComponentForm,
    DrawingForm,
    DynamicQRCodeForm,
    ExcelImportBatchForm,
    LevelForm,
    PremiseForm,
    QRReplacementForm,
    RoomForm,
    MaintenanceRequestForm,
)

from .models import (
    AssetDocument,
    AssetLabel,
    Block,
    Component,
    Drawing,
    DynamicQRCode,
    ExcelImportBatch,
    Level,
    Premise,
    Room,
    MaintenanceRequest,
)

from .utils.sorting import apply_sorting

# =========================================================
# DASHBOARD
# =========================================================

@login_required
def dashboard(request):
    context = {
        "premise_count": Premise.objects.count(),
        "block_count": Block.objects.count(),
        "level_count": Level.objects.count(),
        "room_count": Room.objects.count(),
        "component_count": Component.objects.count(),
    }

    return render(
        request,
        "assets/dashboard.html",
        context,
    )


# =========================================================
# COMPONENT PUBLIC DETAIL
# =========================================================

def component_public_detail(request, public_id):
    component = get_object_or_404(
        Component,
        public_id=public_id,
    )

    can_view_details = False

    if component.security_level == "public":
        can_view_details = True

    elif (
        component.security_level == "staff"
        and request.user.is_authenticated
    ):
        can_view_details = True

    elif (
        component.security_level == "restricted"
        and request.user.is_superuser
    ):
        can_view_details = True

    return render(
        request,
        "assets/component_public_detail.html",
        {
            "component": component,
            "can_view_details": can_view_details,
        },
    )


def component_qr_code(
    request,
    public_id,
):
    # =====================================================
    # GET COMPONENT
    # =====================================================

    component = get_object_or_404(
        Component,
        public_id=public_id,
    )


    # =====================================================
    # PUBLIC COMPONENT URL
    # =====================================================
    #
    # QR will point to:
    #
    # /component/<public_id>/
    #
    # =====================================================

    scan_url = (
        request.build_absolute_uri(
            reverse(
                "assets:component_public_detail",
                kwargs={
                    "public_id": (
                        component.public_id
                    ),
                },
            )
        )
    )


    # =====================================================
    # GENERATE QR
    # =====================================================

    qr_image = qrcode.make(
        scan_url
    )


    # =====================================================
    # SAVE QR INTO MEMORY
    # =====================================================

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)


    # =====================================================
    # RETURN PNG
    # =====================================================

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    response[
        "Content-Disposition"
    ] = (
        f'inline; filename="'
        f'{component.component_id}.png"'
    )

    return response

    # =============================================
    # FIND EXISTING ACTIVE COMPONENT QR
    # =============================================

    dynamic_qr = (
        DynamicQRCode.objects
        .filter(
            qr_type="component",
            component=component,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    # =============================================
    # CREATE ONE IF COMPONENT DOES NOT HAVE QR
    # =============================================

    if dynamic_qr is None:

        base_qr_id = (
            f"QR-COMP-{component.pk}"
        )

        qr_id = base_qr_id
        number = 2

        while DynamicQRCode.objects.filter(
            qr_id=qr_id
        ).exists():

            qr_id = (
                f"{base_qr_id}-{number}"
            )

            number += 1


        dynamic_qr = (
            DynamicQRCode.objects.create(
                qr_id=qr_id,
                qr_type="component",
                component=component,
                is_active=True,
            )
        )

    # =============================================
    # USE SAME DYNAMIC QR SCAN PAGE AS MODULE 06
    # =============================================

    scan_path = reverse(
        "assets:qr_scan",
        kwargs={
            "public_id": (
                dynamic_qr.public_id
            ),
        },
    )

    scan_url = (
        request.build_absolute_uri(
            scan_path
        )
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

def room_qr_code(
    request,
    room_id,
):
    room = get_object_or_404(
        Room,
        pk=room_id,
    )

    # =============================================
    # FIND EXISTING ACTIVE ROOM QR
    # =============================================

    dynamic_qr = (
        DynamicQRCode.objects
        .filter(
            qr_type="room",
            room=room,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    # =============================================
    # CREATE QR IF ROOM DOES NOT HAVE ONE
    # =============================================

    if dynamic_qr is None:

        base_qr_id = (
            f"QR-ROOM-{room.room_tag}"
        )

        qr_id = base_qr_id
        number = 2

        while DynamicQRCode.objects.filter(
            qr_id=qr_id
        ).exists():

            qr_id = (
                f"{base_qr_id}-{number}"
            )

            number += 1


        dynamic_qr = (
            DynamicQRCode.objects.create(
                qr_id=qr_id,
                qr_type="room",
                room=room,
                is_active=True,
            )
        )

    # =============================================
    # USE SAME DYNAMIC QR SCAN PAGE
    # =============================================

    scan_path = reverse(
        "assets:qr_scan",
        kwargs={
            "public_id": (
                dynamic_qr.public_id
            ),
        },
    )

    scan_url = (
        request.build_absolute_uri(
            scan_path
        )
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

def level_qr_code(
    request,
    level_id,
):
    level = get_object_or_404(
        Level,
        pk=level_id,
    )

    # =============================================
    # FIND EXISTING ACTIVE LEVEL QR
    # =============================================

    dynamic_qr = (
        DynamicQRCode.objects
        .filter(
            qr_type="level",
            level=level,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    # =============================================
    # CREATE QR IF LEVEL DOES NOT HAVE ONE
    # =============================================

    if dynamic_qr is None:

        base_qr_id = (
            f"QR-LEVEL-{level.block.code}{level.code}"
        )

        qr_id = base_qr_id
        number = 2

        while DynamicQRCode.objects.filter(
            qr_id=qr_id
        ).exists():

            qr_id = (
                f"{base_qr_id}-{number}"
            )

            number += 1

        dynamic_qr = DynamicQRCode.objects.create(
            qr_id=qr_id,
            qr_type="level",
            level=level,
            is_active=True,
        )

    # =============================================
    # USE SAME DYNAMIC QR SCAN PAGE
    # =============================================

    scan_path = reverse(
        "assets:qr_scan",
        kwargs={
            "public_id": dynamic_qr.public_id,
        },
    )

    scan_url = request.build_absolute_uri(
        scan_path
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

def block_qr_code(
    request,
    block_id,
):
    block = get_object_or_404(
        Block,
        pk=block_id,
    )

    # =============================================
    # FIND EXISTING ACTIVE BLOCK QR
    # =============================================

    dynamic_qr = (
        DynamicQRCode.objects
        .filter(
            qr_type="block",
            block=block,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    # =============================================
    # CREATE QR IF BLOCK DOES NOT HAVE ONE
    # =============================================

    if dynamic_qr is None:

        base_qr_id = (
            f"QR-BLOCK-{block.code}"
        )

        qr_id = base_qr_id
        number = 2

        while DynamicQRCode.objects.filter(
            qr_id=qr_id
        ).exists():

            qr_id = (
                f"{base_qr_id}-{number}"
            )

            number += 1

        dynamic_qr = DynamicQRCode.objects.create(
            qr_id=qr_id,
            qr_type="block",
            block=block,
            is_active=True,
        )

    # =============================================
    # USE SAME DYNAMIC QR SCAN PAGE
    # =============================================

    scan_path = reverse(
        "assets:qr_scan",
        kwargs={
            "public_id": dynamic_qr.public_id,
        },
    )

    scan_url = request.build_absolute_uri(
        scan_path
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

def premise_qr_code(
    request,
    premise_id,
):
    premise = get_object_or_404(
        Premise,
        pk=premise_id,
    )

    # =============================================
    # FIND EXISTING ACTIVE PREMISE QR
    # =============================================

    dynamic_qr = (
        DynamicQRCode.objects
        .filter(
            qr_type="premise",
            premise=premise,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    # =============================================
    # CREATE QR IF PREMISE DOES NOT HAVE ONE
    # =============================================

    if dynamic_qr is None:

        base_qr_id = (
            f"QR-PREMISE-{premise.pk}"
        )

        qr_id = base_qr_id
        number = 2

        while DynamicQRCode.objects.filter(
            qr_id=qr_id
        ).exists():

            qr_id = (
                f"{base_qr_id}-{number}"
            )

            number += 1

        dynamic_qr = DynamicQRCode.objects.create(
            qr_id=qr_id,
            qr_type="premise",
            premise=premise,
            is_active=True,
        )

    # =============================================
    # USE SAME DYNAMIC QR SCAN PAGE
    # =============================================

    scan_path = reverse(
        "assets:qr_scan",
        kwargs={
            "public_id": dynamic_qr.public_id,
        },
    )

    scan_url = request.build_absolute_uri(
        scan_path
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

# =========================================================
# PREMISES
# =========================================================
@login_required
def premise_list(request):

    premises = Premise.objects.all()


    # =================================
    # SEARCH
    # =================================

    search = request.GET.get(
        "search"
    )

    state = request.GET.get(
        "state"
    )

    status = request.GET.get(
        "status"
    )


    if search:

        premises = premises.filter(
            Q(name__icontains=search)
            |
            Q(dpa_number__icontains=search)
        )


    if state:

        premises = premises.filter(
            state=state
        )


    if status:

        premises = premises.filter(
            status=status
        )


    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-created_at",

        "oldest": "created_at",

        "name_a": "name",

        "name_z": "-name",

    }


    premises = apply_sorting(
        premises,
        request,
        allowed_sort,
    )


    # =================================
    # DROPDOWN DATA
    # =================================

    states = (
        Premise.objects
        .values_list(
            "state",
            flat=True
        )
        .distinct()
        .order_by(
            "state"
        )
    )


    statuses = (
        Premise.STATUS_CHOICES
    )


    return render(
        request,
        "assets/premise_list.html",
        {

            "premises": premises,

            "states": states,

            "statuses": statuses,

        },
    )


@login_required
def premise_create(request):
    if request.method == "POST":
        form = PremiseForm(
            request.POST
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:premise_list"
            )

    else:
        form = PremiseForm()

    return render(
        request,
        "assets/premise_form.html",
        {
            "form": form,
        },
    )


@login_required
def premise_update(
    request,
    premise_id,
):
    premise = get_object_or_404(
        Premise,
        pk=premise_id,
    )

    if request.method == "POST":
        form = PremiseForm(
            request.POST,
            instance=premise,
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:premise_list"
            )

    else:
        form = PremiseForm(
            instance=premise
        )

    return render(
        request,
        "assets/premise_form.html",
        {
            "form": form,
            "premise": premise,
        },
    )


@login_required
def premise_delete(
    request,
    premise_id,
):
    premise = get_object_or_404(
        Premise,
        pk=premise_id,
    )

    if request.method == "POST":
        premise.delete()

        return redirect(
            "assets:premise_list"
        )

    return render(
        request,
        "assets/premise_confirm_delete.html",
        {
            "premise": premise,
        },
    )


# =========================================================
# BLOCKS
# =========================================================

@login_required
def block_list(request):

    blocks = Block.objects.all()


    # =================================
    # FILTER VALUES
    # =================================

    search = request.GET.get(
        "search"
    )

    premise_name = request.GET.get(
        "premise"
    )

    block_name = request.GET.get(
        "block_name"
    )

    structure_type = request.GET.get(
        "structure_type"
    )

    status = request.GET.get(
        "status"
    )


    # =================================
    # SEARCH
    # =================================

    if search:

        blocks = blocks.filter(

            Q(name__icontains=search)
            |
            Q(code__icontains=search)

        )


    # =================================
    # PREMISE FILTER
    # =================================

    if premise_name:

        blocks = blocks.filter(
            premise__name=premise_name
        )


    # =================================
    # BLOCK NAME FILTER
    # =================================

    if block_name:

        blocks = blocks.filter(
            name=block_name
        )


    # =================================
    # STRUCTURE TYPE FILTER
    # =================================

    if structure_type:

        blocks = blocks.filter(
            structure_type=structure_type
        )


    # =================================
    # STATUS FILTER
    # =================================

    if status:

        blocks = blocks.filter(
            status=status
        )


    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-created_at",

        "oldest": "created_at",

        "name_a": "name",

        "name_z": "-name",

    }


    blocks = apply_sorting(
        blocks,
        request,
        allowed_sort,
    )


    # =================================
    # DROPDOWN DATA
    # =================================

    premises = (
        Premise.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    block_names = (
        Block.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    structure_types = (
        Block.STRUCTURE_TYPE_CHOICES
    )


    statuses = (
        Block.STATUS_CHOICES
    )


    return render(
        request,
        "assets/block_list.html",
        {

            "blocks": blocks,

            "premises": premises,

            "block_names": block_names,

            "structure_types": structure_types,

            "statuses": statuses,

        },
    )



@login_required
def block_create(request):

    if request.method == "POST":

        form = BlockForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            return redirect(
                "assets:block_list"
            )

    else:

        form = BlockForm()


    return render(
        request,
        "assets/block_form.html",
        {
            "form": form,
        },
    )



@login_required
def block_update(
    request,
    block_id,
):

    block = get_object_or_404(
        Block,
        id=block_id,
    )


    if request.method == "POST":

        form = BlockForm(
            request.POST,
            instance=block,
        )


        if form.is_valid():

            form.save()

            return redirect(
                "assets:block_list"
            )


    else:

        form = BlockForm(
            instance=block
        )


    return render(
        request,
        "assets/block_form.html",
        {
            "form": form,
            "block": block,
        },
    )


@login_required
def level_list(request):

    levels = Level.objects.all()


    # =================================
    # FILTER VALUES
    # =================================

    search = request.GET.get(
        "search"
    )

    premise_name = request.GET.get(
        "premise"
    )

    block_name = request.GET.get(
        "block_name"
    )

    level_name = request.GET.get(
        "level_name"
    )


    # =================================
    # SEARCH
    # =================================

    if search:

        levels = levels.filter(

            Q(name__icontains=search)
            |
            Q(code__icontains=search)

        )


    # =================================
    # PREMISE FILTER
    # =================================

    if premise_name:

        levels = levels.filter(
            block__premise__name=premise_name
        )


    # =================================
    # BLOCK FILTER
    # =================================

    if block_name:

        levels = levels.filter(
            block__name=block_name
        )


    # =================================
    # LEVEL NAME FILTER
    # =================================

    if level_name:

        levels = levels.filter(
            name=level_name
        )


    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-id",

        "oldest": "id",

        "name_a": "name",

        "name_z": "-name",

    }


    levels = apply_sorting(
        levels,
        request,
        allowed_sort,
    )


    # =================================
    # DROPDOWN DATA
    # =================================

    premises = (
        Premise.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    blocks = (
        Block.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    level_names = (
        Level.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    return render(
        request,
        "assets/level_list.html",
        {

            "levels": levels,

            "premises": premises,

            "blocks": blocks,

            "level_names": level_names,

        },
    )

@login_required
def level_create(request):
    if request.method == "POST":
        form = LevelForm(
            request.POST
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:level_list"
            )

    else:
        form = LevelForm()

    return render(
        request,
        "assets/level_form.html",
        {
            "form": form,
        },
    )


@login_required
def level_update(
    request,
    level_id,
):
    level = get_object_or_404(
        Level,
        pk=level_id,
    )

    if request.method == "POST":
        form = LevelForm(
            request.POST,
            instance=level,
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:level_list"
            )

    else:
        form = LevelForm(
            instance=level
        )

    return render(
        request,
        "assets/level_form.html",
        {
            "form": form,
            "level": level,
        },
    )


@login_required
def level_delete(
    request,
    level_id,
):
    level = get_object_or_404(
        Level,
        pk=level_id,
    )

    if request.method == "POST":
        level.delete()

        return redirect(
            "assets:level_list"
        )

    return render(
        request,
        "assets/level_confirm_delete.html",
        {
            "level": level,
        },
    )


# =========================================================
# ROOMS & OPEN AREAS
# =========================================================


@login_required
def room_create(request):

    if request.method == "POST":

        form = RoomForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            return redirect(
                "assets:room_list"
            )


    else:

        form = RoomForm()


    return render(
        request,
        "assets/room_form.html",
        {
            "form": form,
            "page_title": "Add Room / Open Area",
            "button_text": "Create Room",
        },
    )



@login_required
def room_list(request):

    rooms = Room.objects.all()



    # =================================
    # FILTER VALUES
    # =================================

    search = request.GET.get(
        "search"
    )

    premise = request.GET.get(
        "premise"
    )

    block_name = request.GET.get(
        "block_name"
    )

    level_name = request.GET.get(
        "level_name"
    )

    room_name = request.GET.get(
        "room_name"
    )

    space_type = request.GET.get(
        "space_type"
    )



    # =================================
    # SEARCH
    # =================================

    if search:

        rooms = rooms.filter(

            Q(room_tag__icontains=search)
            |
            Q(code__icontains=search)
            |
            Q(name__icontains=search)

        )



    # =================================
    # PREMISE FILTER
    # =================================

    if premise:

        rooms = rooms.filter(
            level__block__premise__name=premise
        )



    # =================================
    # BLOCK FILTER
    # =================================

    if block_name:

        rooms = rooms.filter(
            level__block__name=block_name
        )



    # =================================
    # LEVEL FILTER
    # =================================

    if level_name:

        rooms = rooms.filter(
            level__name=level_name
        )



    # =================================
    # ROOM NAME FILTER
    # =================================

    if room_name:

        rooms = rooms.filter(
            name=room_name
        )



    # =================================
    # SPACE TYPE FILTER
    # =================================

    if space_type:

        rooms = rooms.filter(
            space_type=space_type
        )



    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-id",

        "oldest": "id",

        "code_a": "code",

        "code_z": "-code",

        "name_a": "name",

        "name_z": "-name",

    }


    rooms = apply_sorting(
        rooms,
        request,
        allowed_sort,
    )



    # =================================
    # DROPDOWN DATA
    # =================================


    premises = (
        Premise.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )



    blocks = (
        Block.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )



    levels = (
        Level.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )



    room_names = (
        Room.objects
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )



    space_types = (
        Room.SPACE_TYPE_CHOICES
    )



    return render(
        request,
        "assets/room_list.html",
        {

            "rooms": rooms,

            "premises": premises,

            "blocks": blocks,

            "levels": levels,

            "room_names": room_names,

            "space_types": space_types,

        },
    )





@login_required
def room_update(
    request,
    room_id,
):

    room = get_object_or_404(
        Room,
        pk=room_id,
    )


    if request.method == "POST":

        form = RoomForm(
            request.POST,
            instance=room,
        )


        if form.is_valid():

            form.save()

            return redirect(
                "assets:room_list"
            )


    else:

        form = RoomForm(
            instance=room
        )


    return render(
        request,
        "assets/room_form.html",
        {
            "form": form,
            "room": room,
            "page_title": (
                f"Edit Room — {room.room_tag}"
            ),
            "button_text": "Save Changes",
        },
    )





@login_required
def room_edit(
    request,
    room_id,
):

    return room_update(
        request,
        room_id,
    )





@login_required
def room_delete(
    request,
    room_id,
):

    room = get_object_or_404(
        Room,
        pk=room_id,
    )


    if request.method == "POST":

        room.delete()

        return redirect(
            "assets:room_list"
        )


    return render(
        request,
        "assets/room_confirm_delete.html",
        {
            "room": room,
        },
    )


# =========================================================
# COMPONENTS
# =========================================================

@login_required
def component_list(request):

    components = Component.objects.all()


    # =================================
    # FILTER VALUES
    # =================================

    search = request.GET.get(
        "search"
    )

    premise = request.GET.get(
        "premise"
    )

    block_name = request.GET.get(
        "block_name"
    )

    level_name = request.GET.get(
        "level_name"
    )

    room_name = request.GET.get(
        "room_name"
    )

    component_name = request.GET.get(
        "component_name"
    )

    discipline = request.GET.get(
        "discipline"
    )

    system = request.GET.get(
        "system"
    )

    status = request.GET.get(
        "status"
    )


    # =================================
    # SEARCH
    # =================================

    if search:

        components = components.filter(

            Q(component_id__icontains=search)
            |
            Q(name__icontains=search)
            |
            Q(component_code__icontains=search)
            |
            Q(serial_number__icontains=search)
            |
            Q(brand__icontains=search)
            |
            Q(model__icontains=search)

        )


    # =================================
    # PREMISE FILTER
    # =================================

    if premise:

        components = components.filter(
            room__level__block__premise__name=premise
        )


    # =================================
    # BLOCK FILTER
    # =================================

    if block_name:

        components = components.filter(
            room__level__block__name=block_name
        )


    # =================================
    # LEVEL FILTER
    # =================================

    if level_name:

        components = components.filter(
            room__level__name=level_name
        )


    # =================================
    # ROOM FILTER
    # =================================

    if room_name:

        components = components.filter(
            room__name=room_name
        )


    # =================================
    # COMPONENT NAME FILTER
    # =================================

    if component_name:

        components = components.filter(
            name=component_name
        )


    # =================================
    # DISCIPLINE FILTER
    # =================================

    if discipline:

        components = components.filter(
            discipline=discipline
        )


    # =================================
    # SYSTEM FILTER
    # =================================

    if system:

        components = components.filter(
            system=system
        )


    # =================================
    # STATUS FILTER
    # =================================

    if status:

        components = components.filter(
            status=status
        )


    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-id",

        "oldest": "id",

        "component_id_a": "component_id",

        "component_id_z": "-component_id",

        "name_a": "name",

        "name_z": "-name",

        "status": "status",

    }


    components = apply_sorting(
        components,
        request,
        allowed_sort,
    )


    # =================================
    # UNIQUE DROPDOWN DATA
    # =================================

    premises = (
        Premise.objects
        .values_list(
            "name",
            flat=True
        )
        .exclude(
            name=""
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    blocks = (
        Block.objects
        .values_list(
            "name",
            flat=True
        )
        .exclude(
            name=""
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    levels = (
        Level.objects
        .values_list(
            "name",
            flat=True
        )
        .exclude(
            name=""
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    rooms = (
        Room.objects
        .values_list(
            "name",
            flat=True
        )
        .exclude(
            name=""
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    component_names = (
        Component.objects
        .values_list(
            "name",
            flat=True
        )
        .exclude(
            name=""
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    systems = (
        Component.objects
        .values_list(
            "system",
            flat=True
        )
        .exclude(
            system=""
        )
        .distinct()
        .order_by(
            "system"
        )
    )


    disciplines = (
        Component.DISCIPLINE_CHOICES
    )


    statuses = (
        Component.STATUS_CHOICES
    )


    return render(
        request,
        "assets/component_list.html",
        {
            "components": components,

            "premises": premises,

            "blocks": blocks,

            "levels": levels,

            "rooms": rooms,

            "component_names": component_names,

            "disciplines": disciplines,

            "systems": systems,

            "statuses": statuses,
        },
    )

@login_required
def component_create(request):

    if request.method == "POST":

        form = ComponentForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            return redirect(
                "assets:component_list"
            )

    else:

        form = ComponentForm()


    return render(
        request,
        "assets/component_form.html",
        {
            "form": form,
            "page_title": "Add Component",
            "button_text": "Create Component",
        },
    )

@login_required
def component_update(
    request,
    component_id,
):
    component = get_object_or_404(
        Component,
        pk=component_id,
    )

    if request.method == "POST":
        form = ComponentForm(
            request.POST,
            instance=component,
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:component_list"
            )

    else:
        form = ComponentForm(
            instance=component
        )

    return render(
        request,
        "assets/component_form.html",
        {
            "form": form,
            "component": component,
        },
    )


@login_required
def component_delete(
    request,
    component_id,
):
    component = get_object_or_404(
        Component,
        pk=component_id,
    )

    if request.method == "POST":
        component.delete()

        return redirect(
            "assets:component_list"
        )

    return render(
        request,
        "assets/component_confirm_delete.html",
        {
            "component": component,
        },
    )


# =========================================================
# ASSET LABELS
# =========================================================

@login_required
def label_list(request):
    labels = AssetLabel.objects.select_related(
        "premise",
        "block",
        "room",
        "component",
    ).all()

    return render(
        request,
        "assets/label_list.html",
        {
            "labels": labels,
        },
    )


# =========================================================
# DYNAMIC QR
# =========================================================
def qr_scan(
    request,
    public_id,
):
    qr = get_object_or_404(
        DynamicQRCode.objects.select_related(
            "premise",
            "block",
            "block__premise",
            "level",
            "level__block",
            "level__block__premise",
            "room",
            "room__level",
            "room__level__block",
            "room__level__block__premise",
            "component",
            "component__room",
            "component__room__level",
            "component__room__level__block",
            "component__room__level__block__premise",
        ),
        public_id=public_id,
    )


    # =================================================
    # INACTIVE / REPLACED QR
    # =================================================

    if not qr.is_active:

        current_qr = qr
        latest_replacement = None
        visited_ids = set()


        while current_qr.replaced_by_id:

            if current_qr.pk in visited_ids:
                break


            visited_ids.add(
                current_qr.pk
            )


            current_qr = (
                current_qr.replaced_by
            )


            latest_replacement = (
                current_qr
            )


        return render(
            request,
            "assets/qr_inactive.html",
            {
                "qr": qr,
                "latest_replacement": (
                    latest_replacement
                ),
            },
            status=410,
        )


    # =================================================
    # UPDATE SCAN COUNT
    # =================================================

    DynamicQRCode.objects.filter(
        pk=qr.pk
    ).update(
        last_scan=timezone.now(),
        scan_count=F("scan_count") + 1,
    )


    qr.refresh_from_db()


    # =================================================
    # STAFF-ONLY DRAWINGS AND DOCUMENTS
    # =================================================

    related_drawings = Drawing.objects.none()

    related_documents = (
        AssetDocument.objects.none()
    )


    if request.user.is_authenticated:


        # ---------------------------------------------
        # COMPONENT QR
        # ---------------------------------------------

        if (
            qr.qr_type == "component"
            and qr.component
        ):

            related_drawings = (
                Drawing.objects
                .filter(
                    component=qr.component
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "drawing_number",
                    "-revision",
                )
            )


            related_documents = (
                AssetDocument.objects
                .filter(
                    component=qr.component
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "document_number"
                )
            )


        # ---------------------------------------------
        # ROOM QR
        # ---------------------------------------------

        elif (
            qr.qr_type == "room"
            and qr.room
        ):

            related_drawings = (
                Drawing.objects
                .filter(
                    room=qr.room,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "drawing_number",
                    "-revision",
                )
            )


            related_documents = (
                AssetDocument.objects
                .filter(
                    room=qr.room,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "document_number"
                )
            )


        # ---------------------------------------------
        # LEVEL QR
        # ---------------------------------------------

        elif (
            qr.qr_type == "level"
            and qr.level
        ):

            related_drawings = (
                Drawing.objects
                .filter(
                    level=qr.level,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "drawing_number",
                    "-revision",
                )
            )


            related_documents = (
                AssetDocument.objects
                .filter(
                    level=qr.level,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "document_number"
                )
            )


        # ---------------------------------------------
        # BLOCK QR
        # ---------------------------------------------

        elif (
            qr.qr_type == "block"
            and qr.block
        ):

            related_drawings = (
                Drawing.objects
                .filter(
                    block=qr.block,
                    level__isnull=True,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "drawing_number",
                    "-revision",
                )
            )


            related_documents = (
                AssetDocument.objects
                .filter(
                    block=qr.block,
                    level__isnull=True,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "document_number"
                )
            )


        # ---------------------------------------------
        # PREMISE QR
        # ---------------------------------------------

        elif (
            qr.qr_type == "premise"
            and qr.premise
        ):

            related_drawings = (
                Drawing.objects
                .filter(
                    premise=qr.premise,
                    block__isnull=True,
                    level__isnull=True,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "drawing_number",
                    "-revision",
                )
            )


            related_documents = (
                AssetDocument.objects
                .filter(
                    premise=qr.premise,
                    block__isnull=True,
                    level__isnull=True,
                    room__isnull=True,
                    component__isnull=True,
                )
                .select_related(
                    "premise",
                    "block",
                    "level",
                    "room",
                    "component",
                )
                .order_by(
                    "document_number"
                )
            )


    # =================================================
    # RENDER
    # =================================================

    return render(
        request,
        "assets/qr_scan.html",
        {
            "qr": qr,

            "reported_request_no": (
                request.GET.get(
                    "reported"
                )
            ),

            "related_drawings":
                related_drawings,

            "related_documents":
                related_documents,
        },
    )

def qr_scan_legacy(
    request,
    qr_id,
):
    qr = get_object_or_404(
        DynamicQRCode,
        qr_id=qr_id,
    )

    return redirect(
        "assets:qr_scan",
        public_id=qr.public_id,
    )


@login_required
def qr_code_list(request):

    qr_codes = (
        DynamicQRCode.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
        )
        .all()
    )


    # =================================
    # FILTER VALUES
    # =================================

    search = request.GET.get(
        "search"
    )

    qr_type = request.GET.get(
        "qr_type"
    )

    status = request.GET.get(
        "status"
    )

    premise_name = request.GET.get(
        "premise"
    )

    block_name = request.GET.get(
        "block_name"
    )

    level_name = request.GET.get(
        "level_name"
    )

    room_name = request.GET.get(
        "room_name"
    )

    component_name = request.GET.get(
        "component_name"
    )


    # =================================
    # SEARCH
    # =================================

    if search:

        qr_codes = qr_codes.filter(

            Q(
                qr_id__icontains=search
            )
            |
            Q(
                public_id__icontains=search
            )
            |
            Q(
                premise__name__icontains=search
            )
            |
            Q(
                block__name__icontains=search
            )
            |
            Q(
                level__name__icontains=search
            )
            |
            Q(
                room__name__icontains=search
            )
            |
            Q(
                room__room_tag__icontains=search
            )
            |
            Q(
                component__name__icontains=search
            )
            |
            Q(
                component__component_id__icontains=search
            )

        )


    # =================================
    # QR TYPE FILTER
    # =================================

    if qr_type:

        qr_codes = qr_codes.filter(
            qr_type=qr_type
        )


    # =================================
    # STATUS FILTER
    # =================================

    if status == "active":

        qr_codes = qr_codes.filter(
            is_active=True
        )

    elif status == "inactive":

        qr_codes = qr_codes.filter(
            is_active=False
        )


    # =================================
    # PREMISE FILTER
    # =================================

    if premise_name:

        qr_codes = qr_codes.filter(

            Q(
                premise__name=premise_name
            )
            |
            Q(
                block__premise__name=premise_name
            )
            |
            Q(
                level__block__premise__name=premise_name
            )
            |
            Q(
                room__level__block__premise__name=premise_name
            )
            |
            Q(
                component__room__level__block__premise__name=premise_name
            )

        )


    # =================================
    # BLOCK FILTER
    # =================================

    if block_name:

        qr_codes = qr_codes.filter(

            Q(
                block__name=block_name
            )
            |
            Q(
                level__block__name=block_name
            )
            |
            Q(
                room__level__block__name=block_name
            )
            |
            Q(
                component__room__level__block__name=block_name
            )

        )


    # =================================
    # LEVEL FILTER
    # =================================

    if level_name:

        qr_codes = qr_codes.filter(

            Q(
                level__name=level_name
            )
            |
            Q(
                room__level__name=level_name
            )
            |
            Q(
                component__room__level__name=level_name
            )

        )


    # =================================
    # ROOM FILTER
    # =================================

    if room_name:

        qr_codes = qr_codes.filter(

            Q(
                room__name=room_name
            )
            |
            Q(
                component__room__name=room_name
            )

        )


    # =================================
    # COMPONENT FILTER
    # =================================

    if component_name:

        qr_codes = qr_codes.filter(
            component__name=component_name
        )


    # =================================
    # SORTING
    # =================================

    allowed_sort = {

        "newest": "-id",

        "oldest": "id",

        "type": "qr_type",

        "scan_high": "-scan_count",

        "scan_low": "scan_count",

        "active": "-is_active",

        "inactive": "is_active",

    }


    qr_codes = apply_sorting(
        qr_codes,
        request,
        allowed_sort,
    )


    # =================================
    # UNIQUE DROPDOWN DATA
    # =================================

    premises = (
        Premise.objects
        .exclude(
            name=""
        )
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    blocks = (
        Block.objects
        .exclude(
            name=""
        )
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    levels = (
        Level.objects
        .exclude(
            name=""
        )
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    rooms = (
        Room.objects
        .exclude(
            name=""
        )
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    components = (
        Component.objects
        .exclude(
            name=""
        )
        .values_list(
            "name",
            flat=True
        )
        .distinct()
        .order_by(
            "name"
        )
    )


    qr_types = (
        DynamicQRCode.QR_TYPE_CHOICES
    )


    return render(
        request,
        "assets/qr_code_list.html",
        {
            "qr_codes": qr_codes,

            "premises": premises,

            "blocks": blocks,

            "levels": levels,

            "rooms": rooms,

            "components": components,

            "qr_types": qr_types,
        },
    )


@login_required
def qr_code_create(request):
    if request.method == "POST":
        form = DynamicQRCodeForm(
            request.POST
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:qr_code_list"
            )

    else:
        form = DynamicQRCodeForm()

    return render(
        request,
        "assets/qr_code_form.html",
        {
            "form": form,
            "page_title": (
                "Create Dynamic QR Code"
            ),
            "button_text": (
                "Create QR Code"
            ),
        },
    )


@login_required
def qr_code_edit(
    request,
    qr_id,
):
    qr_code = get_object_or_404(
        DynamicQRCode,
        public_id=qr_id,
    )

    if request.method == "POST":
        form = DynamicQRCodeForm(
            request.POST,
            instance=qr_code,
        )

        if form.is_valid():
            form.save()

            return redirect(
                "assets:qr_code_list"
            )

    else:
        form = DynamicQRCodeForm(
            instance=qr_code
        )

    return render(
        request,
        "assets/qr_code_form.html",
        {
            "form": form,
            "page_title": (
                f"Edit QR Code — "
                f"{qr_code.qr_id}"
            ),
            "button_text": (
                "Save Changes"
            ),
        },
    )


def get_next_replacement_qr_id(
    current_qr_id,
):
    match = re.fullmatch(
        r"(.+)-R(\d+)",
        current_qr_id,
    )

    if match:
        base_qr_id = match.group(1)

        replacement_number = (
            int(match.group(2)) + 1
        )

    else:
        base_qr_id = current_qr_id
        replacement_number = 2

    suggested_id = (
        f"{base_qr_id}-"
        f"R{replacement_number}"
    )

    while DynamicQRCode.objects.filter(
        qr_id=suggested_id
    ).exists():
        replacement_number += 1

        suggested_id = (
            f"{base_qr_id}-"
            f"R{replacement_number}"
        )

    return suggested_id


@login_required
def qr_code_replace(
    request,
    qr_id,
):
    old_qr = get_object_or_404(
        DynamicQRCode,
        public_id=qr_id,
    )

    if old_qr.replaced_by:
        return redirect(
            "assets:qr_code_list"
        )

    if request.method == "POST":
        form = QRReplacementForm(
            request.POST
        )

        if form.is_valid():
            with transaction.atomic():

                new_qr = (
                    DynamicQRCode.objects.create(
                        qr_id=(
                            form.cleaned_data[
                                "new_qr_id"
                            ]
                        ),
                        qr_type=old_qr.qr_type,
                        premise=old_qr.premise,
                        block=old_qr.block,
                        level=old_qr.level,
                        room=old_qr.room,
                        component=old_qr.component,
                        is_active=True,
                    )
                )

                old_qr.is_active = False
                old_qr.replaced_by = new_qr

                old_qr.replacement_reason = (
                    form.cleaned_data[
                        "replacement_reason"
                    ]
                )

                old_qr.deactivated_at = (
                    timezone.now()
                )

                old_qr.save(
                    update_fields=[
                        "is_active",
                        "replaced_by",
                        "replacement_reason",
                        "deactivated_at",
                    ]
                )

            return redirect(
                "assets:qr_code_list"
            )

    else:
        suggested_id = (
            get_next_replacement_qr_id(
                old_qr.qr_id
            )
        )

        form = QRReplacementForm(
            initial={
                "new_qr_id": suggested_id,
            }
        )

    return render(
        request,
        "assets/qr_code_replace.html",
        {
            "form": form,
            "old_qr": old_qr,
        },
    )


@login_required
def qr_label_preview(
    request,
    qr_id,
):
    qr_code = get_object_or_404(
        DynamicQRCode,
        public_id=qr_id,
    )

    return render(
        request,
        "assets/qr_label_preview.html",
        {
            "qr": qr_code,
        },
    )


def dynamic_qr_image(
    request,
    qr_id,
):
    qr = get_object_or_404(
        DynamicQRCode,
        public_id=qr_id,
        is_active=True,
    )

    scan_url = (
        request.build_absolute_uri(
            reverse(
                "assets:qr_scan",
                kwargs={
                    "public_id": qr.public_id,
                },
            )
        )
    )

    qr_image = qrcode.make(
        scan_url
    )

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    response["Content-Disposition"] = (
        f'inline; filename="'
        f'{qr.public_id}.png"'
    )

    return response


@login_required
def dynamic_qr_download(
    request,
    qr_id,
):
    qr = get_object_or_404(
        DynamicQRCode,
        public_id=qr_id,
        is_active=True,
    )

    scan_url = (
        request.build_absolute_uri(
            reverse(
                "assets:qr_scan",
                kwargs={
                    "public_id": (
                        qr.public_id
                    ),
                },
            )
        )
    )

    qr_image = qrcode.make(
        scan_url
    )

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="'
        f'{qr.qr_id}.png"'
    )

    return response


# =========================================================
# DRAWINGS & DOCUMENTS
# =========================================================
@login_required
def drawing_list(request):

    # =================================================
    # BASE QUERIES
    # =================================================

    drawings = (
        Drawing.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "uploaded_by",
        )
        .all()
    )

    documents = (
        AssetDocument.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "uploaded_by",
        )
        .all()
    )


    # =================================================
    # DRAWING FILTERS
    # =================================================

    drawing_search = request.GET.get(
        "drawing_search",
        "",
    ).strip()

    drawing_type = request.GET.get(
        "drawing_type",
        "",
    )

    drawing_status = request.GET.get(
        "drawing_status",
        "",
    )

    drawing_premise = request.GET.get(
        "drawing_premise",
        "",
    )


    if drawing_search:

        drawings = drawings.filter(

            Q(
                drawing_number__icontains=drawing_search
            )
            |
            Q(
                title__icontains=drawing_search
            )
            |
            Q(
                description__icontains=drawing_search
            )
            |
            Q(
                block__name__icontains=drawing_search
            )
            |
            Q(
                room__name__icontains=drawing_search
            )
            |
            Q(
                component__name__icontains=drawing_search
            )

        )


    if drawing_type:

        drawings = drawings.filter(
            drawing_type=drawing_type
        )


    if drawing_status:

        drawings = drawings.filter(
            status=drawing_status
        )


    if drawing_premise:

        drawings = drawings.filter(
            premise_id=drawing_premise
        )


    # =================================================
    # DOCUMENT FILTERS
    # =================================================

    document_search = request.GET.get(
        "document_search",
        "",
    ).strip()

    document_type = request.GET.get(
        "document_type",
        "",
    )

    document_status = request.GET.get(
        "document_status",
        "",
    )

    document_premise = request.GET.get(
        "document_premise",
        "",
    )


    if document_search:

        documents = documents.filter(

            Q(
                document_number__icontains=document_search
            )
            |
            Q(
                title__icontains=document_search
            )
            |
            Q(
                description__icontains=document_search
            )
            |
            Q(
                block__name__icontains=document_search
            )
            |
            Q(
                room__name__icontains=document_search
            )
            |
            Q(
                component__name__icontains=document_search
            )

        )


    if document_type:

        documents = documents.filter(
            document_type=document_type
        )


    if document_status:

        documents = documents.filter(
            status=document_status
        )


    if document_premise:

        documents = documents.filter(
            premise_id=document_premise
        )


    # =================================================
    # ORDERING
    # =================================================

    drawings = drawings.order_by(
        "drawing_number",
        "-revision",
    )

    documents = documents.order_by(
        "document_number",
    )


    # =================================================
    # FILTER OPTIONS
    # =================================================

    premises = Premise.objects.order_by(
        "name"
    )


    # =================================================
    # RENDER
    # =================================================

    return render(
        request,
        "assets/drawing_list.html",
        {
            "drawings": drawings,
            "documents": documents,

            "premises": premises,

            "drawing_types":
                Drawing.DRAWING_TYPE_CHOICES,

            "drawing_statuses":
                Drawing.STATUS_CHOICES,

            "document_types":
                AssetDocument.DOCUMENT_TYPE_CHOICES,

            "document_statuses":
                AssetDocument.STATUS_CHOICES,

            "drawing_search":
                drawing_search,

            "drawing_type_selected":
                drawing_type,

            "drawing_status_selected":
                drawing_status,

            "drawing_premise_selected":
                drawing_premise,

            "document_search":
                document_search,

            "document_type_selected":
                document_type,

            "document_status_selected":
                document_status,

            "document_premise_selected":
                document_premise,
        },
    )


@login_required
def drawing_create(request):
    if request.method == "POST":
        form = DrawingForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            drawing = form.save(
                commit=False
            )

            drawing.uploaded_by = (
                request.user
            )

            drawing.save()

            return redirect(
                "assets:drawing_list"
            )

    else:
        form = DrawingForm()

    return render(
        request,
        "assets/drawing_form.html",
        {
            "form": form,
            "page_title": (
                "Upload Drawing"
            ),
            "button_text": (
                "Upload Drawing"
            ),
        },
    )


@login_required
def drawing_edit(
    request,
    drawing_id,
):
    drawing = get_object_or_404(
        Drawing,
        pk=drawing_id,
    )

    if request.method == "POST":
        form = DrawingForm(
            request.POST,
            request.FILES,
            instance=drawing,
        )

        if form.is_valid():
            updated_drawing = (
                form.save(commit=False)
            )

            updated_drawing.uploaded_by = (
                request.user
            )

            updated_drawing.save()

            return redirect(
                "assets:drawing_list"
            )

    else:
        form = DrawingForm(
            instance=drawing
        )

    return render(
        request,
        "assets/drawing_form.html",
        {
            "form": form,
            "page_title": (
                f"Edit Drawing — "
                f"{drawing.drawing_number}"
            ),
            "button_text": (
                "Save Changes"
            ),
        },
    )


@login_required
def drawing_archive(
    request,
    drawing_id,
):
    drawing = get_object_or_404(
        Drawing,
        pk=drawing_id,
    )

    if request.method == "POST":
        drawing.status = "archived"

        drawing.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return redirect(
            "assets:drawing_list"
        )

    return render(
        request,
        "assets/drawing_archive_confirm.html",
        {
            "drawing": drawing,
        },
    )


@login_required
def drawing_download(
    request,
    drawing_id,
):
    drawing = get_object_or_404(
        Drawing,
        pk=drawing_id,
    )

    if not drawing.file:
        raise Http404(
            "Drawing file not found."
        )

    return FileResponse(
        drawing.file.open("rb"),
        as_attachment=False,
        filename=Path(
            drawing.file.name
        ).name,
    )


@login_required
def drawing_new_revision(
    request,
    drawing_id,
):
    previous_drawing = get_object_or_404(
        Drawing,
        pk=drawing_id,
    )

    if request.method == "POST":
        form = DrawingForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            with transaction.atomic():

                new_drawing = (
                    form.save(
                        commit=False
                    )
                )

                new_drawing.uploaded_by = (
                    request.user
                )

                new_drawing.status = (
                    "current"
                )

                Drawing.objects.filter(
                    drawing_number=(
                        new_drawing.drawing_number
                    ),
                    status="current",
                ).update(
                    status="superseded"
                )

                new_drawing.save()

            return redirect(
                "assets:drawing_list"
            )

    else:
        form = DrawingForm(
            initial={
                "premise": (
                    previous_drawing.premise
                ),
                "block": (
                    previous_drawing.block
                ),
                "level": (
                    previous_drawing.level
                ),
                "room": (
                    previous_drawing.room
                ),
                "component": (
                    previous_drawing.component
                ),
                "drawing_number": (
                    previous_drawing.drawing_number
                ),
                "title": (
                    previous_drawing.title
                ),
                "drawing_type": (
                    previous_drawing.drawing_type
                ),
                "description": (
                    previous_drawing.description
                ),
                "status": "current",
            }
        )

    return render(
        request,
        "assets/drawing_form.html",
        {
            "form": form,
            "page_title": (
                f"Upload New Revision — "
                f"{previous_drawing.drawing_number}"
            ),
            "button_text": (
                "Upload New Revision"
            ),
        },
    )


# =========================================================
# ASSET DOCUMENTS
# =========================================================

@login_required
def asset_document_list(request):
    return redirect(
        reverse(
            "assets:drawing_list"
        )
        + "#documents"
    )


@login_required
def asset_document_create(request):
    if request.method == "POST":
        form = AssetDocumentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            document = form.save(
                commit=False
            )

            document.uploaded_by = (
                request.user
            )

            document.save()

            return redirect(
                reverse(
                    "assets:drawing_list"
                )
                + "#documents"
            )

    else:
        form = AssetDocumentForm()

    return render(
        request,
        "assets/asset_document_form.html",
        {
            "form": form,
            "page_title": (
                "Upload Asset Document"
            ),
            "button_text": (
                "Upload Document"
            ),
        },
    )


@login_required
def asset_document_edit(
    request,
    document_id,
):
    document = get_object_or_404(
        AssetDocument,
        pk=document_id,
    )

    if request.method == "POST":
        form = AssetDocumentForm(
            request.POST,
            request.FILES,
            instance=document,
        )

        if form.is_valid():
            updated_document = (
                form.save(
                    commit=False
                )
            )

            updated_document.uploaded_by = (
                request.user
            )

            updated_document.save()

            return redirect(
                reverse(
                    "assets:drawing_list"
                )
                + "#documents"
            )

    else:
        form = AssetDocumentForm(
            instance=document
        )

    return render(
        request,
        "assets/asset_document_form.html",
        {
            "form": form,
            "page_title": (
                f"Edit Document — "
                f"{document.document_number}"
            ),
            "button_text": (
                "Save Changes"
            ),
        },
    )


@login_required
def asset_document_download(
    request,
    document_id,
):
    document = get_object_or_404(
        AssetDocument,
        pk=document_id,
    )

    if not document.file:
        raise Http404(
            "Document file not found."
        )

    return FileResponse(
        document.file.open("rb"),
        as_attachment=False,
        filename=Path(
            document.file.name
        ).name,
    )


@login_required
def asset_document_archive(
    request,
    document_id,
):
    document = get_object_or_404(
        AssetDocument,
        pk=document_id,
    )

    if request.method == "POST":
        document.status = "archived"

        document.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return redirect(
            reverse(
                "assets:drawing_list"
            )
            + "#documents"
        )

    return render(
        request,
        "assets/asset_document_archive_confirm.html",
        {
            "document": document,
        },
    )


# =========================================================
# EXCEL / DA6 IMPORT
# =========================================================

@login_required
def excel_import_create(request):

    if request.method == "POST":

        form = ExcelImportBatchForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            # =================================================
            # CREATE IMPORT BATCH
            # =================================================

            import_batch = form.save(
                commit=False
            )

            import_batch.uploaded_by = (
                request.user
            )

            # New workflow is always Full DA6.
            import_batch.import_type = (
                "full_da6"
            )

            import_batch.premise = None

            import_batch.status = (
                "uploaded"
            )

            import_batch.total_rows = 0

            import_batch.successful_rows = 0

            import_batch.failed_rows = 0

            import_batch.error_log = ""

            import_batch.import_sheet = ""

            import_batch.save()


            # =================================================
            # 1. VALIDATE BASIC DA6 WORKBOOK STRUCTURE
            # =================================================

            validation = (
                validate_full_da6_file(
                    import_batch.file.path
                )
            )

            import_batch.total_rows = (
                validation[
                    "total_rows"
                ]
            )


            # -------------------------------------------------
            # INVALID WORKBOOK STRUCTURE
            # -------------------------------------------------

            if not validation["valid"]:

                import_batch.status = (
                    "failed"
                )

                import_batch.error_log = (
                    "\n".join(
                        validation[
                            "errors"
                        ]
                    )
                )


            # -------------------------------------------------
            # WORKBOOK HAS NO IMPORTABLE DATA
            # -------------------------------------------------

            elif (
                validation[
                    "total_rows"
                ]
                == 0
            ):

                import_batch.status = (
                    "failed"
                )

                import_batch.error_log = (
                    "The DA6 workbook structure "
                    "is valid, but no importable "
                    "Block, Room or Component "
                    "records were found. "
                    "Please upload a completed "
                    "DA6 workbook."
                )


            else:

                # =================================================
                # 2. READ DPA AND FIND / CREATE PREMISE
                # =================================================

                premise_result = (
                    get_or_create_premise_from_workbook(
                        import_batch.file.path
                    )
                )


                # -------------------------------------------------
                # PREMISE / DPA ERROR
                # -------------------------------------------------

                if not premise_result[
                    "success"
                ]:

                    import_batch.status = (
                        "failed"
                    )

                    import_batch.error_log = (
                        "\n".join(
                            premise_result[
                                "errors"
                            ]
                        )
                    )


                else:

                    premise = (
                        premise_result[
                            "premise"
                        ]
                    )

                    premise_was_created = (
                        premise_result[
                            "created"
                        ]
                    )


                    # =================================================
                    # 3. VALIDATE DAK BLOK AGAINST PREMISE
                    # =================================================

                    block_validation = (
                        validate_da6_block_rows(
                            import_batch.file.path,
                            premise,
                        )
                    )


                    if not block_validation[
                        "valid"
                    ]:

                        # ---------------------------------------------
                        # If this import just created a brand-new
                        # Premise but the DA6 data is invalid,
                        # remove the empty Premise again.
                        #
                        # Existing Premises are NEVER deleted.
                        # ---------------------------------------------

                        if premise_was_created:

                            try:

                                premise.delete()

                            except Exception:
                                pass


                        import_batch.premise = (
                            None
                        )

                        import_batch.status = (
                            "failed"
                        )

                        import_batch.failed_rows = (
                            block_validation[
                                "total_rows"
                            ]
                        )

                        import_batch.error_log = (
                            "\n".join(
                                block_validation[
                                    "errors"
                                ]
                            )
                        )


                    else:

                        # =================================================
                        # 4. ATTACH DETECTED PREMISE TO IMPORT BATCH
                        # =================================================

                        import_batch.premise = (
                            premise
                        )

                        import_batch.status = (
                            "validated"
                        )

                        import_batch.failed_rows = 0

                        import_batch.error_log = ""


            # =================================================
            # SAVE FINAL VALIDATION RESULT
            # =================================================

            import_batch.save(
                update_fields=[
                    "premise",
                    "import_type",
                    "import_sheet",
                    "status",
                    "total_rows",
                    "successful_rows",
                    "failed_rows",
                    "error_log",
                    "updated_at",
                ]
            )


            return redirect(
                "assets:excel_import_detail",
                batch_id=import_batch.id,
            )


    else:

        form = ExcelImportBatchForm()


    return render(
        request,
        "assets/excel_import_form.html",
        {
            "form": form,
        },
    )

@login_required
def excel_import_detail(
    request,
    batch_id,
):
    import_batch = get_object_or_404(
        ExcelImportBatch,
        pk=batch_id,
    )

    return render(
        request,
        "assets/excel_import_detail.html",
        {
            "import_batch": import_batch,
        },
    )

@login_required
def excel_import_execute(
    request,
    batch_id,
):
    import_batch = get_object_or_404(
        ExcelImportBatch,
        pk=batch_id,
    )


    # =====================================================
    # POST ONLY
    # =====================================================

    if request.method != "POST":
        return redirect(
            "assets:excel_import_detail",
            batch_id=import_batch.id,
        )


    # =====================================================
    # VALIDATED FULL DA6 ONLY
    # =====================================================

    if (
        import_batch.import_type
        != "full_da6"
        or import_batch.status
        != "validated"
    ):
        return redirect(
            "assets:excel_import_detail",
            batch_id=import_batch.id,
        )


    # =====================================================
    # PREMISE MUST ALREADY BE DETECTED
    # =====================================================

    if not import_batch.premise:

        import_batch.status = "failed"

        import_batch.failed_rows = (
            import_batch.total_rows
        )

        import_batch.error_log = (
            "No Premise is attached to this "
            "import batch. The DPA Number "
            "could not be resolved."
        )

        import_batch.save(
            update_fields=[
                "status",
                "failed_rows",
                "error_log",
                "updated_at",
            ]
        )

        return redirect(
            "assets:excel_import_detail",
            batch_id=import_batch.id,
        )


    errors = []


    try:

        with transaction.atomic():

            # =================================================
            # 1. BLOCKS
            # =================================================

            block_result = (
                import_da6_blocks(
                    import_batch.file.path,
                    import_batch.premise,
                )
            )


            if not block_result[
                "success"
            ]:

                errors.extend(
                    block_result[
                        "errors"
                    ]
                )

                raise ValueError(
                    "DAK Blok import failed."
                )


            # =================================================
            # 2. LEVELS + ROOMS
            # =================================================

            room_result = (
                import_da6_rooms(
                    import_batch.file.path,
                    import_batch.premise,
                )
            )


            if not room_result[
                "success"
            ]:

                errors.extend(
                    room_result[
                        "errors"
                    ]
                )

                raise ValueError(
                    "DAKRuang import failed."
                )


            # =================================================
            # 3. COMPONENTS
            # =================================================

            component_result = (
                import_da6_components(
                    import_batch.file.path,
                    import_batch.premise,
                )
            )


            if not component_result[
                "success"
            ]:

                errors.extend(
                    component_result[
                        "errors"
                    ]
                )

                raise ValueError(
                    "DAKKomponen import failed."
                )


            # =================================================
            # IMPORT COUNTS
            # =================================================

            blocks_created = (
                block_result[
                    "created"
                ]
            )

            blocks_skipped = (
                block_result[
                    "skipped"
                ]
            )


            levels_created = (
                room_result[
                    "levels_created"
                ]
            )


            rooms_created = (
                room_result[
                    "rooms_created"
                ]
            )

            rooms_skipped = (
                room_result[
                    "rooms_skipped"
                ]
            )


            components_created = (
                component_result[
                    "created"
                ]
            )

            components_skipped = (
                component_result[
                    "skipped"
                ]
            )


            # =================================================
            # SUCCESSFUL / PROCESSED ROWS
            # =================================================
            #
            # A skipped existing record is still considered
            # successfully processed because it is an
            # intentional duplicate, not an import failure.
            #
            # =================================================

            successful_rows = (
                blocks_created
                + blocks_skipped
                + rooms_created
                + rooms_skipped
                + components_created
                + components_skipped
            )


            # =================================================
            # COMPLETE IMPORT
            # =================================================

            import_batch.status = (
                "completed"
            )

            import_batch.successful_rows = (
                successful_rows
            )

            import_batch.failed_rows = 0

            import_batch.error_log = ""

            import_batch.save(
                update_fields=[
                    "status",
                    "successful_rows",
                    "failed_rows",
                    "error_log",
                    "updated_at",
                ]
            )


    except Exception as error:

        # =====================================================
        # IMPORT FAILED
        # =====================================================

        if not errors:
            errors.append(
                str(error)
            )


        import_batch.status = (
            "failed"
        )

        import_batch.successful_rows = 0

        import_batch.failed_rows = (
            import_batch.total_rows
        )

        import_batch.error_log = (
            "\n".join(
                errors
            )
        )

        import_batch.save(
            update_fields=[
                "status",
                "successful_rows",
                "failed_rows",
                "error_log",
                "updated_at",
            ]
        )


    return redirect(
        "assets:excel_import_detail",
        batch_id=import_batch.id,
    )

@login_required
def maintenance_dashboard(request):

    total_open = (
        MaintenanceRequest.objects
        .filter(status="submitted")
        .count()
    )

    total_assigned = (
        MaintenanceRequest.objects
        .filter(status="assigned")
        .count()
    )

    total_progress = (
        MaintenanceRequest.objects
        .filter(status="in_progress")
        .count()
    )

    total_completed = (
        MaintenanceRequest.objects
        .filter(status="completed")
        .count()
    )

    total_closed = (
        MaintenanceRequest.objects
        .filter(status="closed")
        .count()
    )

    total_critical = (
        MaintenanceRequest.objects
        .filter(
            priority="critical"
        )
        .exclude(
            status__in=[
                "completed",
                "closed",
                "rejected",
            ]
        )
        .count()
    )


    recent_requests = (
        MaintenanceRequest.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
        )
        .order_by("-created_at")[:10]
    )


    context = {
        "total_open": total_open,
        "total_assigned": total_assigned,
        "total_progress": total_progress,
        "total_completed": total_completed,
        "total_closed": total_closed,
        "total_critical": total_critical,
        "recent_requests": recent_requests,
    }


    return render(
        request,
        "assets/maintenance_dashboard.html",
        context,
    )

@login_required
def maintenance_request_list(request):

    maintenance_requests = (
        MaintenanceRequest.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "reported_by",
            "assigned_to",
        )
        .order_by("-created_at")
    )

    status = request.GET.get("status")
    priority = request.GET.get("priority")
    active_only = request.GET.get("active")

    if status:
        maintenance_requests = (
            maintenance_requests.filter(
                status=status
            )
        )

    if priority:
        maintenance_requests = (
            maintenance_requests.filter(
                priority=priority
            )
        )

    if active_only == "1":
        maintenance_requests = (
            maintenance_requests.exclude(
                status__in=[
                    "completed",
                    "closed",
                    "rejected",
                ]
            )
        )

    return render(
        request,
        "assets/maintenance_request_list.html",
        {
            "maintenance_requests": maintenance_requests,
        },
    )

@login_required
def maintenance_request_detail(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest.objects.select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "reported_by",
            "assigned_to",
        ),
        pk=request_id,
    )

    return render(
        request,
        "assets/maintenance_request_detail.html",
        {
            "maintenance_request": maintenance_request,
        },
    )

@login_required
def maintenance_request_assign(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        pk=request_id,
    )

    if request.method == "POST":

        technician_id = request.POST.get(
            "technician"
        )

        if technician_id:
            technician = get_object_or_404(
                User,
                pk=technician_id,
            )

            maintenance_request.assigned_to = technician
            maintenance_request.status = "assigned"

            maintenance_request.save(
                update_fields=[
                    "assigned_to",
                    "status",
                    "updated_at",
                ]
            )

            return redirect(
                "assets:maintenance_request_detail",
                request_id=maintenance_request.id,
            )

    technicians = (
        User.objects
        .filter(is_active=True)
        .order_by("username")
    )

    return render(
        request,
        "assets/maintenance_request_assign.html",
        {
            "maintenance_request": maintenance_request,
            "technicians": technicians,
        },
    )

@login_required
def maintenance_request_detail(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest.objects.select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "reported_by",
            "assigned_to",
        ),
        pk=request_id,
    )

    technicians = (
        User.objects
        .filter(is_active=True)
        .order_by("username")
    )

    return render(
        request,
        "assets/maintenance_request_detail.html",
        {
            "maintenance_request": maintenance_request,
            "technicians": technicians,
        },
    )

@login_required
def maintenance_request_start(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        pk=request_id,
    )

    if (
        request.method == "POST"
        and maintenance_request.status == "assigned"
    ):
        maintenance_request.status = "in_progress"

        maintenance_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return redirect(
        "assets:maintenance_request_detail",
        request_id=maintenance_request.id,
    )

@login_required
def maintenance_request_complete(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        pk=request_id,
    )

    if (
        request.method == "POST"
        and maintenance_request.status == "in_progress"
    ):
        maintenance_request.status = "completed"

        maintenance_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return redirect(
        "assets:maintenance_request_detail",
        request_id=maintenance_request.id,
    )

@login_required
def maintenance_request_close(
    request,
    request_id,
):

    maintenance_request = get_object_or_404(
        MaintenanceRequest,
        pk=request_id,
    )

    if (
        request.method == "POST"
        and maintenance_request.status == "completed"
    ):
        maintenance_request.status = "closed"

        maintenance_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    return redirect(
        "assets:maintenance_request_detail",
        request_id=maintenance_request.id,
    )

@login_required
def maintenance_request_create(request):

    if request.method == "POST":
        form = MaintenanceRequestForm(
            request.POST
        )

        if form.is_valid():
            maintenance_request = (
                form.save(commit=False)
            )

            maintenance_request.reported_by = (
                request.user
            )

            maintenance_request.status = (
                "submitted"
            )

            maintenance_request.save()

            return redirect(
                "assets:maintenance_request_detail",
                request_id=(
                    maintenance_request.id
                ),
            )

    else:
        form = MaintenanceRequestForm()

    return render(
        request,
        "assets/maintenance_request_form.html",
        {
            "form": form,
        },
    )

@login_required
def maintenance_load_blocks(request):

    premise_id = request.GET.get(
        "premise"
    )

    blocks = (
        Block.objects
        .filter(
            premise_id=premise_id
        )
        .order_by("code")
        .values(
            "id",
            "code",
            "name",
        )
    )

    return JsonResponse(
        {
            "items": list(blocks),
        }
    )


@login_required
def maintenance_load_levels(request):

    block_id = request.GET.get(
        "block"
    )

    levels = (
        Level.objects
        .filter(
            block_id=block_id
        )
        .order_by(
            "sequence",
            "code",
        )
        .values(
            "id",
            "code",
            "name",
        )
    )

    return JsonResponse(
        {
            "items": list(levels),
        }
    )


@login_required
def maintenance_load_rooms(request):

    level_id = request.GET.get(
        "level"
    )

    rooms = (
        Room.objects
        .filter(
            level_id=level_id
        )
        .order_by("code")
        .values(
            "id",
            "room_tag",
            "name",
        )
    )

    return JsonResponse(
        {
            "items": list(rooms),
        }
    )


@login_required
def maintenance_load_components(request):

    room_id = request.GET.get(
        "room"
    )

    components = (
        Component.objects
        .filter(
            room_id=room_id
        )
        .order_by("name")
        .values(
            "id",
            "component_id",
            "name",
        )
    )

    return JsonResponse(
        {
            "items": list(components),
        }
    )

def maintenance_report_from_qr(
    request,
    public_id,
):

    qr = get_object_or_404(
        DynamicQRCode.objects.select_related(
            "premise",
            "block",
            "block__premise",
            "level",
            "level__block",
            "level__block__premise",
            "room",
            "room__level",
            "room__level__block",
            "room__level__block__premise",
            "component",
            "component__room",
            "component__room__level",
            "component__room__level__block",
            "component__room__level__block__premise",
        ),
        public_id=public_id,
        is_active=True,
    )


    premise = None
    block = None
    level = None
    room = None
    component = None


    # =============================================
    # COMPONENT QR
    # =============================================

    if (
        qr.qr_type == "component"
        and qr.component
    ):
        component = qr.component
        room = component.room
        level = room.level
        block = level.block
        premise = block.premise


    # =============================================
    # ROOM QR
    # =============================================

    elif (
        qr.qr_type == "room"
        and qr.room
    ):
        room = qr.room
        level = room.level
        block = level.block
        premise = block.premise


    # =============================================
    # LEVEL QR
    # =============================================

    elif (
        qr.qr_type == "level"
        and qr.level
    ):
        level = qr.level
        block = level.block
        premise = block.premise


    # =============================================
    # BLOCK QR
    # =============================================

    elif (
        qr.qr_type == "block"
        and qr.block
    ):
        block = qr.block
        premise = block.premise


    # =============================================
    # PREMISE QR
    # =============================================

    elif (
        qr.qr_type == "premise"
        and qr.premise
    ):
        premise = qr.premise


    # =============================================
    # SUBMIT REPORT
    # =============================================

    if request.method == "POST":

        post_data = request.POST.copy()

        post_data["premise"] = (
            premise.id
            if premise
            else ""
        )

        post_data["block"] = (
            block.id
            if block
            else ""
        )

        post_data["level"] = (
            level.id
            if level
            else ""
        )

        post_data["room"] = (
            room.id
            if room
            else ""
        )

        post_data["component"] = (
            component.id
            if component
            else ""
        )


        form = MaintenanceRequestForm(
            post_data
        )


        if form.is_valid():

            maintenance_request = (
                form.save(commit=False)
            )


            # Lock location to scanned QR.
            maintenance_request.premise = (
                premise
            )

            maintenance_request.block = (
                block
            )

            maintenance_request.level = (
                level
            )

            maintenance_request.room = (
                room
            )

            maintenance_request.component = (
                component
            )


            if request.user.is_authenticated:
                maintenance_request.reported_by = (
                    request.user
                )


            maintenance_request.status = (
                "submitted"
            )


            # Save QR source if qr_code field exists.
            maintenance_request.qr_code = qr


            maintenance_request.save()


            return redirect(
                (
                    reverse(
                        "assets:qr_scan",
                        kwargs={
                            "public_id": (
                                qr.public_id
                            ),
                        },
                    )
                    + "?reported="
                    + maintenance_request.request_no
                )
            )


    else:

        form = MaintenanceRequestForm(
            initial={
                "premise": (
                    premise
                ),
                "block": (
                    block
                ),
                "level": (
                    level
                ),
                "room": (
                    room
                ),
                "component": (
                    component
                ),
            }
        )


    return render(
        request,
        "assets/maintenance_report_from_qr.html",
        {
            "form": form,
            "qr": qr,
            "premise": premise,
            "block": block,
            "level": level,
            "room": room,
            "component": component,
        },
    )

@login_required
def reports_dashboard(request):

    return render(
        request,
        "assets/reports_dashboard.html",
    )
@login_required
def asset_report(request):

    # =========================================================
    # REPORT TYPE
    # =========================================================

    report_types = [
        ("component", "Asset Components"),
        ("room", "Rooms & Open Areas"),
        ("level", "Levels"),
        ("block", "Blocks & External Structures"),
        ("premise", "Premises"),
    ]

    report_type = request.GET.get(
        "report_type",
        "component",
    )


    # =========================================================
    # FILTER VALUES
    # =========================================================

    search = request.GET.get(
        "search",
        "",
    ).strip()

    premise_id = request.GET.get(
        "premise",
        "",
    )

    block_id = request.GET.get(
        "block",
        "",
    )

    level_id = request.GET.get(
        "level",
        "",
    )

    room_id = request.GET.get(
        "room",
        "",
    )

    status = request.GET.get(
        "status",
        "",
    )


    # =========================================================
    # FILTER DROPDOWN DATA
    # =========================================================

    premises = Premise.objects.order_by(
        "name"
    )

    blocks = (
        Block.objects
        .select_related("premise")
        .order_by(
            "premise__name",
            "code",
        )
    )

    levels = (
        Level.objects
        .select_related(
            "block",
            "block__premise",
        )
        .order_by(
            "block__code",
            "sequence",
        )
    )

    rooms = (
        Room.objects
        .select_related(
            "level",
            "level__block",
            "level__block__premise",
        )
        .order_by(
            "room_tag"
        )
    )


    # =========================================================
    # COMPONENT REPORT
    # =========================================================

    if report_type == "component":

        report_items = (
            Component.objects
            .select_related(
                "room",
                "room__level",
                "room__level__block",
                "room__level__block__premise",
            )
            .order_by(
                "room__level__block__premise__name",
                "room__level__block__code",
                "room__level__code",
                "room__room_tag",
                "component_id",
            )
        )


        if search:

            report_items = report_items.filter(

                Q(component_id__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(component_code__icontains=search)
                |
                Q(brand__icontains=search)
                |
                Q(model__icontains=search)
                |
                Q(system__icontains=search)

            )


        if premise_id:

            report_items = report_items.filter(
                room__level__block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                room__level__block_id=block_id
            )


        if level_id:

            report_items = report_items.filter(
                room__level_id=level_id
            )


        if room_id:

            report_items = report_items.filter(
                room_id=room_id
            )


        if status:

            report_items = report_items.filter(
                status=status
            )


        statuses = Component.STATUS_CHOICES



    # =========================================================
    # ROOM / OPEN AREA REPORT
    # =========================================================

    elif report_type == "room":

        report_items = (
            Room.objects
            .select_related(
                "level",
                "level__block",
                "level__block__premise",
                "room_function",
            )
            .order_by(
                "level__block__premise__name",
                "level__block__code",
                "level__sequence",
                "room_tag",
            )
        )


        if search:

            report_items = report_items.filter(

                Q(room_tag__icontains=search)
                |
                Q(code__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(function_code__icontains=search)
                |
                Q(function_name__icontains=search)

            )


        if premise_id:

            report_items = report_items.filter(
                level__block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                level__block_id=block_id
            )


        if level_id:

            report_items = report_items.filter(
                level_id=level_id
            )


        statuses = []



    # =========================================================
    # LEVEL REPORT
    # =========================================================

    elif report_type == "level":

        report_items = (
            Level.objects
            .select_related(
                "block",
                "block__premise",
            )
            .order_by(
                "block__premise__name",
                "block__code",
                "sequence",
            )
        )


        if search:

            report_items = report_items.filter(

                Q(code__icontains=search)
                |
                Q(name__icontains=search)

            )


        if premise_id:

            report_items = report_items.filter(
                block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                block_id=block_id
            )


        statuses = []



    # =========================================================
    # BLOCK / EXTERNAL STRUCTURE REPORT
    # =========================================================

    elif report_type == "block":

        report_items = (
            Block.objects
            .select_related(
                "premise"
            )
            .order_by(
                "premise__name",
                "code",
            )
        )


        if search:

            report_items = report_items.filter(

                Q(code__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(function__icontains=search)

            )


        if premise_id:

            report_items = report_items.filter(
                premise_id=premise_id
            )


        if status:

            report_items = report_items.filter(
                status=status
            )


        statuses = Block.STATUS_CHOICES



    # =========================================================
    # PREMISE REPORT
    # =========================================================

    else:

        report_type = "premise"

        report_items = Premise.objects.order_by(
            "name"
        )


        if search:

            report_items = report_items.filter(
                Q(name__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                id=premise_id
            )


        statuses = []


    # =========================================================
    # PAGE
    # =========================================================

    return render(
        request,
        "assets/asset_report.html",
        {
            "report_items": report_items,

            "report_types": report_types,
            "report_type": report_type,

            "premises": premises,
            "blocks": blocks,
            "levels": levels,
            "rooms": rooms,

            "statuses": statuses,

            "search": search,

            "premise_selected": premise_id,
            "block_selected": block_id,
            "level_selected": level_id,
            "room_selected": room_id,
            "status_selected": status,
        },
    )

@login_required
def asset_report_pdf(request):

    # =========================================================
    # FILTER VALUES
    # =========================================================

    report_type = request.GET.get(
        "report_type",
        "component",
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    premise_id = request.GET.get(
        "premise",
        "",
    )

    block_id = request.GET.get(
        "block",
        "",
    )

    level_id = request.GET.get(
        "level",
        "",
    )

    room_id = request.GET.get(
        "room",
        "",
    )

    status = request.GET.get(
        "status",
        "",
    )


    # =========================================================
    # GET REPORT DATA
    # =========================================================

    if report_type == "component":

        report_title = "Asset Component Register"

        report_items = (
            Component.objects
            .select_related(
                "room",
                "room__level",
                "room__level__block",
                "room__level__block__premise",
            )
            .order_by(
                "room__level__block__premise__name",
                "room__level__block__code",
                "room__level__code",
                "room__room_tag",
                "component_id",
            )
        )

        if search:

            report_items = report_items.filter(
                Q(component_id__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(component_code__icontains=search)
                |
                Q(brand__icontains=search)
                |
                Q(model__icontains=search)
                |
                Q(system__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                room__level__block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                room__level__block_id=block_id
            )


        if level_id:

            report_items = report_items.filter(
                room__level_id=level_id
            )


        if room_id:

            report_items = report_items.filter(
                room_id=room_id
            )


        if status:

            report_items = report_items.filter(
                status=status
            )



    elif report_type == "room":

        report_title = "Room & Open Area Register"

        report_items = (
            Room.objects
            .select_related(
                "level",
                "level__block",
                "level__block__premise",
                "room_function",
            )
            .order_by(
                "level__block__premise__name",
                "level__block__code",
                "level__sequence",
                "room_tag",
            )
        )


        if search:

            report_items = report_items.filter(
                Q(room_tag__icontains=search)
                |
                Q(code__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(function_code__icontains=search)
                |
                Q(function_name__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                level__block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                level__block_id=block_id
            )


        if level_id:

            report_items = report_items.filter(
                level_id=level_id
            )



    elif report_type == "level":

        report_title = "Level Register"

        report_items = (
            Level.objects
            .select_related(
                "block",
                "block__premise",
            )
            .order_by(
                "block__premise__name",
                "block__code",
                "sequence",
            )
        )


        if search:

            report_items = report_items.filter(
                Q(code__icontains=search)
                |
                Q(name__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                block__premise_id=premise_id
            )


        if block_id:

            report_items = report_items.filter(
                block_id=block_id
            )



    elif report_type == "block":

        report_title = "Block & External Structure Register"

        report_items = (
            Block.objects
            .select_related(
                "premise"
            )
            .order_by(
                "premise__name",
                "code",
            )
        )


        if search:

            report_items = report_items.filter(
                Q(code__icontains=search)
                |
                Q(name__icontains=search)
                |
                Q(function__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                premise_id=premise_id
            )


        if status:

            report_items = report_items.filter(
                status=status
            )



    else:

        report_type = "premise"

        report_title = "Premise Register"

        report_items = Premise.objects.order_by(
            "name"
        )


        if search:

            report_items = report_items.filter(
                Q(name__icontains=search)
            )


        if premise_id:

            report_items = report_items.filter(
                id=premise_id
            )


    # =========================================================
    # RESPONSE
    # =========================================================

    filename = (
        report_title
        .lower()
        .replace(" ", "_")
        .replace("&", "and")
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}.pdf"'
    )


    # =========================================================
    # PDF DOCUMENT
    # =========================================================

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )


    styles = getSampleStyleSheet()


    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0B716B"),
        spaceAfter=5 * mm,
    )


    system_style = ParagraphStyle(
        "SystemTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=2 * mm,
    )


    normal_style = ParagraphStyle(
        "NormalReport",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )


    header_style = ParagraphStyle(
        "TableHeader",
        parent=normal_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#08766F"),
        fontSize=8,
        leading=9,
    )


    story = []


    story.append(
        Paragraph(
            "Government Asset Information System",
            system_style,
        )
    )


    story.append(
        Paragraph(
            report_title,
            title_style,
        )
    )


    # =========================================================
    # FILTER SUMMARY
    # =========================================================

    filter_parts = []


    if premise_id:

        premise = Premise.objects.filter(
            pk=premise_id
        ).first()

        if premise:

            filter_parts.append(
                f"Premise: {escape(premise.name)}"
            )


    if block_id:

        block = Block.objects.filter(
            pk=block_id
        ).first()

        if block:

            filter_parts.append(
                f"Block: {escape(block.code)} - {escape(block.name)}"
            )


    if level_id:

        level = Level.objects.filter(
            pk=level_id
        ).first()

        if level:

            filter_parts.append(
                f"Level: {escape(level.code)} - {escape(level.name)}"
            )


    if room_id:

        room = Room.objects.filter(
            pk=room_id
        ).first()

        if room:

            filter_parts.append(
                f"Room / Area: {escape(room.room_tag)} - {escape(room.name)}"
            )


    if status:

        filter_parts.append(
            f"Status: {escape(status.title())}"
        )


    if search:

        filter_parts.append(
            f"Search: {escape(search)}"
        )


    if filter_parts:

        story.append(
            Paragraph(
                " | ".join(filter_parts),
                normal_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )


    story.append(
        Paragraph(
            f"Total Records: {report_items.count()}",
            normal_style,
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # =========================================================
    # HELPER
    # =========================================================

    def cell(value):

        if value is None or value == "":
            value = "-"

        return Paragraph(
            escape(str(value)),
            normal_style,
        )


    def header(value):

        return Paragraph(
            escape(str(value)),
            header_style,
        )


    # =========================================================
    # COMPONENT TABLE
    # =========================================================

    if report_type == "component":

        table_data = [
            [
                header("No."),
                header("Component ID"),
                header("Component"),
                header("Location"),
                header("Discipline"),
                header("System"),
                header("Brand / Model"),
                header("Status"),
            ]
        ]


        for number, component in enumerate(
            report_items,
            start=1,
        ):

            location = (
                f"{component.room.level.block.premise.name}<br/>"
                f"{component.room.level.block.code} - "
                f"{component.room.level.block.name}<br/>"
                f"{component.room.level.code} - "
                f"{component.room.level.name}<br/>"
                f"{component.room.room_tag} - "
                f"{component.room.name}"
            )


            brand_model = component.brand or "-"

            if component.model:

                brand_model += (
                    f"<br/>{component.model}"
                )


            table_data.append(
                [
                    cell(number),
                    cell(component.component_id),
                    cell(component.name),

                    Paragraph(
                        location,
                        normal_style,
                    ),

                    cell(
                        component.get_discipline_display()
                    ),

                    cell(
                        component.system
                    ),

                    Paragraph(
                        brand_model,
                        normal_style,
                    ),

                    cell(
                        component.get_status_display()
                    ),
                ]
            )


        column_widths = [
            12 * mm,
            30 * mm,
            40 * mm,
            62 * mm,
            30 * mm,
            35 * mm,
            34 * mm,
            24 * mm,
        ]


    # =========================================================
    # ROOM TABLE
    # =========================================================

    elif report_type == "room":

        table_data = [
            [
                header("No."),
                header("Room Tag"),
                header("Room / Area"),
                header("Location"),
                header("Space Type"),
                header("Function"),
                header("Area"),
                header("Security"),
            ]
        ]


        for number, room in enumerate(
            report_items,
            start=1,
        ):

            location = (
                f"{room.level.block.premise.name}<br/>"
                f"{room.level.block.code} - "
                f"{room.level.block.name}<br/>"
                f"{room.level.code} - "
                f"{room.level.name}"
            )


            table_data.append(
                [
                    cell(number),
                    cell(room.room_tag),
                    cell(room.name),

                    Paragraph(
                        location,
                        normal_style,
                    ),

                    cell(
                        room.get_space_type_display()
                    ),

                    cell(
                        room.function_name
                    ),

                    cell(
                        room.area
                    ),

                    cell(
                        room.get_security_level_display()
                    ),
                ]
            )


        column_widths = [
            12 * mm,
            32 * mm,
            40 * mm,
            60 * mm,
            32 * mm,
            45 * mm,
            20 * mm,
            28 * mm,
        ]


    # =========================================================
    # LEVEL TABLE
    # =========================================================

    elif report_type == "level":

        table_data = [
            [
                header("No."),
                header("Level Code"),
                header("Level Name"),
                header("Block"),
                header("Premise"),
                header("Sequence"),
            ]
        ]


        for number, level in enumerate(
            report_items,
            start=1,
        ):

            table_data.append(
                [
                    cell(number),
                    cell(level.code),
                    cell(level.name),

                    cell(
                        f"{level.block.code} - "
                        f"{level.block.name}"
                    ),

                    cell(
                        level.block.premise.name
                    ),

                    cell(
                        level.sequence
                    ),
                ]
            )


        column_widths = [
            15 * mm,
            35 * mm,
            55 * mm,
            60 * mm,
            80 * mm,
            25 * mm,
        ]


    # =========================================================
    # BLOCK TABLE
    # =========================================================

    elif report_type == "block":

        table_data = [
            [
                header("No."),
                header("Block Code"),
                header("Name"),
                header("Premise"),
                header("Structure Type"),
                header("Function"),
                header("Security"),
                header("Status"),
            ]
        ]


        for number, block in enumerate(
            report_items,
            start=1,
        ):

            table_data.append(
                [
                    cell(number),
                    cell(block.code),
                    cell(block.name),
                    cell(block.premise.name),

                    cell(
                        block.get_structure_type_display()
                    ),

                    cell(
                        block.function
                    ),

                    cell(
                        block.get_security_level_display()
                    ),

                    cell(
                        block.get_status_display()
                    ),
                ]
            )


        column_widths = [
            12 * mm,
            28 * mm,
            40 * mm,
            55 * mm,
            37 * mm,
            45 * mm,
            30 * mm,
            25 * mm,
        ]


    # =========================================================
    # PREMISE TABLE
    # =========================================================

    else:

        table_data = [
            [
                header("No."),
                header("Premise"),
                header("DPA"),
                header("Ministry"),
                header("Department"),
                header("State"),
                header("Address"),
            ]
        ]


        for number, premise in enumerate(
            report_items,
            start=1,
        ):

            table_data.append(
                [
                    cell(number),
                    cell(premise.name),

                    cell(
                        getattr(
                            premise,
                            "dpa",
                            "-"
                        )
                    ),

                    cell(
                        getattr(
                            premise,
                            "ministry",
                            "-"
                        )
                    ),

                    cell(
                        getattr(
                            premise,
                            "department",
                            "-"
                        )
                    ),

                    cell(
                        getattr(
                            premise,
                            "state",
                            "-"
                        )
                    ),

                    cell(
                        getattr(
                            premise,
                            "address",
                            "-"
                        )
                    ),
                ]
            )


        column_widths = [
            12 * mm,   # No.
            48 * mm,   # Premise
            28 * mm,   # DPA
            42 * mm,   # Ministry
            42 * mm,   # Department
            27 * mm,   # State
            58 * mm,   # Address
        ]


    # =========================================================
    # CREATE TABLE
    # =========================================================

    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )


    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EAF7F5"),
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#08766F"),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#DCE7E9"),
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        table
    )


    # =========================================================
    # BUILD PDF
    # =========================================================

    document.build(
        story
    )

    return response
@login_required
def maintenance_report(request):

    # =========================================================
    # REPORT TYPES
    # =========================================================

    report_types = [
        (
            "request_register",
            "Maintenance Request Register",
        ),
        (
            "status_report",
            "Maintenance Status Report",
        ),
        (
            "component_history",
            "Component Maintenance History",
        ),
    ]


    report_type = request.GET.get(
        "report_type",
        "request_register",
    )


    # =========================================================
    # FILTER VALUES
    # =========================================================

    search = request.GET.get(
        "search",
        "",
    ).strip()


    premise_id = request.GET.get(
        "premise",
        "",
    )


    block_id = request.GET.get(
        "block",
        "",
    )


    level_id = request.GET.get(
        "level",
        "",
    )


    room_id = request.GET.get(
        "room",
        "",
    )


    component_id = request.GET.get(
        "component",
        "",
    )


    category = request.GET.get(
        "category",
        "",
    )


    priority = request.GET.get(
        "priority",
        "",
    )


    status = request.GET.get(
        "status",
        "",
    )


    date_from = request.GET.get(
        "date_from",
        "",
    )


    date_to = request.GET.get(
        "date_to",
        "",
    )


    # =========================================================
    # MAIN QUERY
    # =========================================================

    maintenance_requests = (
        MaintenanceRequest.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "assigned_to",
            "reported_by",
        )
        .order_by(
            "-created_at"
        )
    )


    # =========================================================
    # SEARCH
    # =========================================================

    if search:

        maintenance_requests = (
            maintenance_requests.filter(
                Q(
                    request_no__icontains=search
                )
                |
                Q(
                    description__icontains=search
                )
                |
                Q(
                    reporter_name__icontains=search
                )
                |
                Q(
                    reporter_contact__icontains=search
                )
                |
                Q(
                    component__component_id__icontains=search
                )
                |
                Q(
                    component__name__icontains=search
                )
                |
                Q(
                    room__name__icontains=search
                )
                |
                Q(
                    block__name__icontains=search
                )
            )
        )


    # =========================================================
    # LOCATION FILTERS
    # =========================================================

    if premise_id:

        maintenance_requests = (
            maintenance_requests.filter(
                premise_id=premise_id
            )
        )


    if block_id:

        maintenance_requests = (
            maintenance_requests.filter(
                block_id=block_id
            )
        )


    if level_id:

        maintenance_requests = (
            maintenance_requests.filter(
                level_id=level_id
            )
        )


    if room_id:

        maintenance_requests = (
            maintenance_requests.filter(
                room_id=room_id
            )
        )


    if component_id:

        maintenance_requests = (
            maintenance_requests.filter(
                component_id=component_id
            )
        )


    # =========================================================
    # MAINTENANCE FILTERS
    # =========================================================

    if category:

        maintenance_requests = (
            maintenance_requests.filter(
                category=category
            )
        )


    if priority:

        maintenance_requests = (
            maintenance_requests.filter(
                priority=priority
            )
        )


    if status:

        maintenance_requests = (
            maintenance_requests.filter(
                status=status
            )
        )


    # =========================================================
    # DATE FILTERS
    # =========================================================

    if date_from:

        maintenance_requests = (
            maintenance_requests.filter(
                created_at__date__gte=date_from
            )
        )


    if date_to:

        maintenance_requests = (
            maintenance_requests.filter(
                created_at__date__lte=date_to
            )
        )


    # =========================================================
    # COMPONENT HISTORY
    # =========================================================

    selected_component = None


    if (
        report_type == "component_history"
        and component_id
    ):

        selected_component = (
            Component.objects
            .select_related(
                "room",
                "room__level",
                "room__level__block",
                "room__level__block__premise",
            )
            .filter(
                pk=component_id
            )
            .first()
        )


    # =========================================================
    # FILTER DROPDOWN DATA
    # =========================================================

    premises = (
        Premise.objects
        .order_by(
            "name"
        )
    )


    blocks = (
        Block.objects
        .select_related(
            "premise"
        )
        .order_by(
            "premise__name",
            "code",
        )
    )


    levels = (
        Level.objects
        .select_related(
            "block",
            "block__premise",
        )
        .order_by(
            "block__premise__name",
            "block__code",
            "sequence",
        )
    )


    rooms = (
        Room.objects
        .select_related(
            "level",
            "level__block",
            "level__block__premise",
        )
        .order_by(
            "room_tag"
        )
    )


    components = (
        Component.objects
        .select_related(
            "room",
            "room__level",
            "room__level__block",
        )
        .order_by(
            "component_id"
        )
    )


    # =========================================================
    # PAGE
    # =========================================================

    return render(
        request,
        "assets/maintenance_report.html",
        {
            "maintenance_requests":
                maintenance_requests,

            "report_types":
                report_types,

            "report_type":
                report_type,

            "selected_component":
                selected_component,

            "premises":
                premises,

            "blocks":
                blocks,

            "levels":
                levels,

            "rooms":
                rooms,

            "components":
                components,

            "categories":
                MaintenanceRequest.CATEGORY_CHOICES,

            "priorities":
                MaintenanceRequest.PRIORITY_CHOICES,

            "statuses":
                MaintenanceRequest.STATUS_CHOICES,

            "search":
                search,

            "premise_selected":
                premise_id,

            "block_selected":
                block_id,

            "level_selected":
                level_id,

            "room_selected":
                room_id,

            "component_selected":
                component_id,

            "category_selected":
                category,

            "priority_selected":
                priority,

            "status_selected":
                status,

            "date_from":
                date_from,

            "date_to":
                date_to,
        },
    )

@login_required
def maintenance_report_pdf(request):

    # =========================================================
    # FILTER VALUES
    # =========================================================

    report_type = request.GET.get(
        "report_type",
        "request_register",
    )

    search = request.GET.get(
        "search",
        "",
    ).strip()

    premise_id = request.GET.get(
        "premise",
        "",
    )

    block_id = request.GET.get(
        "block",
        "",
    )

    level_id = request.GET.get(
        "level",
        "",
    )

    room_id = request.GET.get(
        "room",
        "",
    )

    component_id = request.GET.get(
        "component",
        "",
    )

    category = request.GET.get(
        "category",
        "",
    )

    priority = request.GET.get(
        "priority",
        "",
    )

    status = request.GET.get(
        "status",
        "",
    )

    date_from = request.GET.get(
        "date_from",
        "",
    )

    date_to = request.GET.get(
        "date_to",
        "",
    )


    # =========================================================
    # QUERY
    # =========================================================

    maintenance_requests = (
        MaintenanceRequest.objects
        .select_related(
            "premise",
            "block",
            "level",
            "room",
            "component",
            "assigned_to",
            "reported_by",
        )
        .order_by("-created_at")
    )


    # =========================================================
    # SEARCH
    # =========================================================

    if search:

        maintenance_requests = maintenance_requests.filter(

            Q(request_no__icontains=search)
            |
            Q(description__icontains=search)
            |
            Q(reporter_name__icontains=search)
            |
            Q(reporter_contact__icontains=search)
            |
            Q(component__component_id__icontains=search)
            |
            Q(component__name__icontains=search)
            |
            Q(room__name__icontains=search)
            |
            Q(block__name__icontains=search)

        )


    # =========================================================
    # LOCATION FILTERS
    # =========================================================

    if premise_id:

        maintenance_requests = maintenance_requests.filter(
            premise_id=premise_id
        )


    if block_id:

        maintenance_requests = maintenance_requests.filter(
            block_id=block_id
        )


    if level_id:

        maintenance_requests = maintenance_requests.filter(
            level_id=level_id
        )


    if room_id:

        maintenance_requests = maintenance_requests.filter(
            room_id=room_id
        )


    if component_id:

        maintenance_requests = maintenance_requests.filter(
            component_id=component_id
        )


    # =========================================================
    # MAINTENANCE FILTERS
    # =========================================================

    if category:

        maintenance_requests = maintenance_requests.filter(
            category=category
        )


    if priority:

        maintenance_requests = maintenance_requests.filter(
            priority=priority
        )


    if status:

        maintenance_requests = maintenance_requests.filter(
            status=status
        )


    # =========================================================
    # DATE FILTERS
    # =========================================================

    if date_from:

        maintenance_requests = maintenance_requests.filter(
            created_at__date__gte=date_from
        )


    if date_to:

        maintenance_requests = maintenance_requests.filter(
            created_at__date__lte=date_to
        )


    # =========================================================
    # REPORT TITLE
    # =========================================================

    if report_type == "component_history":

        report_title = "Component Maintenance History"

    elif report_type == "status_report":

        report_title = "Maintenance Status Report"

    else:

        report_type = "request_register"

        report_title = "Maintenance Request Register"


    # =========================================================
    # RESPONSE
    # =========================================================

    filename = (
        report_title
        .lower()
        .replace(" ", "_")
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}.pdf"'
    )


    # =========================================================
    # DOCUMENT
    # =========================================================

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )


    styles = getSampleStyleSheet()


    title_style = ParagraphStyle(
        "MaintenanceTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0B716B"),
        spaceAfter=5 * mm,
    )


    system_style = ParagraphStyle(
        "MaintenanceSystem",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=2 * mm,
    )


    normal_style = ParagraphStyle(
        "MaintenanceNormal",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9.5,
    )


    header_style = ParagraphStyle(
        "MaintenanceHeader",
        parent=normal_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#08766F"),
        fontSize=7.5,
        leading=9,
    )


    story = []


    story.append(
        Paragraph(
            "Government Asset Information System",
            system_style,
        )
    )


    story.append(
        Paragraph(
            report_title,
            title_style,
        )
    )


    # =========================================================
    # FILTER SUMMARY
    # =========================================================

    filter_parts = []


    if premise_id:

        premise = Premise.objects.filter(
            pk=premise_id
        ).first()

        if premise:

            filter_parts.append(
                f"Premise: {escape(premise.name)}"
            )


    if block_id:

        block = Block.objects.filter(
            pk=block_id
        ).first()

        if block:

            filter_parts.append(
                f"Block: {escape(block.code)} - {escape(block.name)}"
            )


    if level_id:

        level = Level.objects.filter(
            pk=level_id
        ).first()

        if level:

            filter_parts.append(
                f"Level: {escape(level.code)} - {escape(level.name)}"
            )


    if room_id:

        room = Room.objects.filter(
            pk=room_id
        ).first()

        if room:

            filter_parts.append(
                f"Room / Area: {escape(room.room_tag)} - {escape(room.name)}"
            )


    if component_id:

        component = Component.objects.filter(
            pk=component_id
        ).first()

        if component:

            filter_parts.append(
                f"Component: {escape(component.component_id)} - {escape(component.name)}"
            )


    if category:

        filter_parts.append(
            f"Category: {escape(category.title())}"
        )


    if priority:

        filter_parts.append(
            f"Priority: {escape(priority.title())}"
        )


    if status:

        filter_parts.append(
            f"Status: {escape(status.replace('_', ' ').title())}"
        )


    if date_from:

        filter_parts.append(
            f"From: {escape(date_from)}"
        )


    if date_to:

        filter_parts.append(
            f"To: {escape(date_to)}"
        )


    if search:

        filter_parts.append(
            f"Search: {escape(search)}"
        )


    if filter_parts:

        story.append(
            Paragraph(
                " | ".join(filter_parts),
                normal_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )


    story.append(
        Paragraph(
            f"Total Records: {maintenance_requests.count()}",
            normal_style,
        )
    )

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # =========================================================
    # HELPERS
    # =========================================================

    def cell(value):

        if value is None or value == "":
            value = "-"

        return Paragraph(
            escape(str(value)),
            normal_style,
        )


    def multiline_cell(lines):

        clean_lines = []

        for line in lines:

            if line:

                clean_lines.append(
                    escape(str(line))
                )

        if not clean_lines:

            clean_lines = ["-"]

        return Paragraph(
            "<br/>".join(clean_lines),
            normal_style,
        )


    def header(value):

        return Paragraph(
            escape(str(value)),
            header_style,
        )


    # =========================================================
    # TABLE HEADER
    # =========================================================

    table_data = [
        [
            header("No."),
            header("Request No."),
            header("Asset / Location"),
            header("Issue"),
            header("Category"),
            header("Priority"),
            header("Status"),
            header("Assigned To"),
            header("Reported"),
        ]
    ]


    # =========================================================
    # TABLE ROWS
    # =========================================================

    for number, maintenance in enumerate(
        maintenance_requests,
        start=1,
    ):

        location_lines = []


        if maintenance.component:

            location_lines.append(
                f"{maintenance.component.component_id} - "
                f"{maintenance.component.name}"
            )


        if maintenance.premise:

            location_lines.append(
                maintenance.premise.name
            )


        if maintenance.block:

            location_lines.append(
                f"{maintenance.block.code} - "
                f"{maintenance.block.name}"
            )


        if maintenance.level:

            location_lines.append(
                f"{maintenance.level.code} - "
                f"{maintenance.level.name}"
            )


        if maintenance.room:

            location_lines.append(
                f"{maintenance.room.room_tag} - "
                f"{maintenance.room.name}"
            )


        if maintenance.assigned_to:

            assigned_name = (
                maintenance.assigned_to.get_full_name()
                or maintenance.assigned_to.username
            )

        else:

            assigned_name = "Not Assigned"


        reported_date = timezone.localtime(
            maintenance.created_at
        ).strftime(
            "%d %b %Y"
        )


        table_data.append(
            [
                cell(number),

                cell(
                    maintenance.request_no
                ),

                multiline_cell(
                    location_lines
                ),

                cell(
                    maintenance.description
                ),

                cell(
                    maintenance.get_category_display()
                ),

                cell(
                    maintenance.get_priority_display()
                ),

                cell(
                    maintenance.get_status_display()
                ),

                cell(
                    assigned_name
                ),

                cell(
                    reported_date
                ),
            ]
        )


    # =========================================================
    # TABLE WIDTHS
    # =========================================================

    column_widths = [
        10 * mm,   # No.
        23 * mm,   # Request
        55 * mm,   # Location
        55 * mm,   # Issue
        25 * mm,   # Category
        22 * mm,   # Priority
        24 * mm,   # Status
        32 * mm,   # Assigned
        27 * mm,   # Reported
    ]


    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )


    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EAF7F5"),
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#08766F"),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#DCE7E9"),
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        table
    )


    # =========================================================
    # BUILD PDF
    # =========================================================

    document.build(
        story
    )

    return response
@login_required
def handover_report(request):

    # =========================================================
    # SELECTED PREMISE
    # =========================================================

    premise_id = request.GET.get(
        "premise",
        "",
    )

    selected_premise = None


    # Empty querysets until a premise is selected

    blocks = Block.objects.none()
    levels = Level.objects.none()
    rooms = Room.objects.none()
    components = Component.objects.none()

    drawings = Drawing.objects.none()
    documents = AssetDocument.objects.none()

    qr_codes = DynamicQRCode.objects.none()

    outstanding_maintenance = (
        MaintenanceRequest.objects.none()
    )


    # =========================================================
    # LOAD SELECTED PREMISE DATA
    # =========================================================

    if premise_id:

        selected_premise = get_object_or_404(
            Premise,
            pk=premise_id,
        )


        # -----------------------------------------------------
        # BLOCKS / EXTERNAL STRUCTURES
        # -----------------------------------------------------

        blocks = (
            Block.objects
            .filter(
                premise=selected_premise
            )
            .order_by(
                "code"
            )
        )


        # -----------------------------------------------------
        # LEVELS
        # -----------------------------------------------------

        levels = (
            Level.objects
            .filter(
                block__premise=selected_premise
            )
            .select_related(
                "block"
            )
            .order_by(
                "block__code",
                "sequence",
            )
        )


        # -----------------------------------------------------
        # ROOMS / OPEN AREAS
        # -----------------------------------------------------

        rooms = (
            Room.objects
            .filter(
                level__block__premise=selected_premise
            )
            .select_related(
                "level",
                "level__block",
            )
            .order_by(
                "room_tag"
            )
        )


        # -----------------------------------------------------
        # COMPONENTS
        # -----------------------------------------------------

        components = (
            Component.objects
            .filter(
                room__level__block__premise=
                    selected_premise
            )
            .select_related(
                "room",
                "room__level",
                "room__level__block",
            )
            .order_by(
                "component_id"
            )
        )


        # -----------------------------------------------------
        # DRAWINGS
        # -----------------------------------------------------

        drawings = (
            Drawing.objects
            .filter(
                premise=selected_premise
            )
            .order_by(
                "drawing_number",
                "-revision",
            )
        )


        # -----------------------------------------------------
        # DOCUMENTS
        # -----------------------------------------------------

        documents = (
            AssetDocument.objects
            .filter(
                premise=selected_premise
            )
            .order_by(
                "document_number"
            )
        )


        # -----------------------------------------------------
        # ALL QR LABELS UNDER THIS PREMISE
        # -----------------------------------------------------

        qr_codes = (
            DynamicQRCode.objects
            .filter(
                Q(
                    premise=selected_premise
                )
                |
                Q(
                    block__premise=
                        selected_premise
                )
                |
                Q(
                    level__block__premise=
                        selected_premise
                )
                |
                Q(
                    room__level__block__premise=
                        selected_premise
                )
                |
                Q(
                    component__room__level__block__premise=
                        selected_premise
                )
            )
            .distinct()
            .order_by(
                "qr_type",
                "qr_id",
            )
        )


        # -----------------------------------------------------
        # OUTSTANDING MAINTENANCE
        # -----------------------------------------------------

        outstanding_maintenance = (
            MaintenanceRequest.objects
            .filter(
                premise=selected_premise
            )
            .exclude(
                status__in=[
                    "closed",
                    "rejected",
                ]
            )
            .select_related(
                "block",
                "level",
                "room",
                "component",
                "assigned_to",
            )
            .order_by(
                "-created_at"
            )
        )


    # =========================================================
    # PREMISE DROPDOWN
    # =========================================================

    premises = (
        Premise.objects
        .order_by(
            "name"
        )
    )


    # =========================================================
    # HANDOVER READINESS
    # =========================================================

    checklist = {
        "premise": bool(
            selected_premise
        ),

        "blocks": (
            blocks.exists()
            if selected_premise
            else False
        ),

        "levels": (
            levels.exists()
            if selected_premise
            else False
        ),

        "rooms": (
            rooms.exists()
            if selected_premise
            else False
        ),

        "components": (
            components.exists()
            if selected_premise
            else False
        ),

        "qr_codes": (
            qr_codes.exists()
            if selected_premise
            else False
        ),

        "drawings": (
            drawings.exists()
            if selected_premise
            else False
        ),

        "documents": (
            documents.exists()
            if selected_premise
            else False
        ),
    }


    # =========================================================
    # PAGE
    # =========================================================

    return render(
        request,
        "assets/handover_report.html",
        {
            "premises":
                premises,

            "selected_premise":
                selected_premise,

            "premise_selected":
                premise_id,


            # DATA

            "blocks":
                blocks,

            "levels":
                levels,

            "rooms":
                rooms,

            "components":
                components,

            "drawings":
                drawings,

            "documents":
                documents,

            "qr_codes":
                qr_codes,

            "outstanding_maintenance":
                outstanding_maintenance,


            # COUNTS

            "block_count":
                blocks.count(),

            "level_count":
                levels.count(),

            "room_count":
                rooms.count(),

            "component_count":
                components.count(),

            "qr_count":
                qr_codes.count(),

            "drawing_count":
                drawings.count(),

            "document_count":
                documents.count(),

            "outstanding_maintenance_count":
                outstanding_maintenance.count(),


            # CHECKLIST

            "checklist":
                checklist,
        },
    )

@login_required
def handover_report_pdf(request):

    # =========================================================
    # PREMISE
    # =========================================================

    premise_id = request.GET.get(
        "premise",
        "",
    )

    selected_premise = get_object_or_404(
        Premise,
        pk=premise_id,
    )


    # =========================================================
    # DATA
    # =========================================================

    blocks = Block.objects.filter(
        premise=selected_premise
    )

    levels = Level.objects.filter(
        block__premise=selected_premise
    )

    rooms = Room.objects.filter(
        level__block__premise=selected_premise
    )

    components = Component.objects.filter(
        room__level__block__premise=selected_premise
    )


    drawings = (
        Drawing.objects
        .filter(
            premise=selected_premise
        )
        .order_by(
            "drawing_number",
            "-revision",
        )
    )


    documents = (
        AssetDocument.objects
        .filter(
            premise=selected_premise
        )
        .order_by(
            "document_number"
        )
    )


    qr_codes = (
        DynamicQRCode.objects
        .filter(
            Q(
                premise=selected_premise
            )
            |
            Q(
                block__premise=selected_premise
            )
            |
            Q(
                level__block__premise=selected_premise
            )
            |
            Q(
                room__level__block__premise=selected_premise
            )
            |
            Q(
                component__room__level__block__premise=
                    selected_premise
            )
        )
        .distinct()
    )


    outstanding_maintenance = (
        MaintenanceRequest.objects
        .filter(
            premise=selected_premise
        )
        .exclude(
            status__in=[
                "closed",
                "rejected",
            ]
        )
        .select_related(
            "block",
            "level",
            "room",
            "component",
            "assigned_to",
        )
        .order_by(
            "-created_at"
        )
    )


    # =========================================================
    # COUNTS
    # =========================================================

    block_count = blocks.count()
    level_count = levels.count()
    room_count = rooms.count()
    component_count = components.count()

    qr_count = qr_codes.count()
    drawing_count = drawings.count()
    document_count = documents.count()

    outstanding_count = (
        outstanding_maintenance.count()
    )


    # =========================================================
    # PDF RESPONSE
    # =========================================================

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="handover_record.pdf"'
    )


    document = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),

        leftMargin=12 * mm,
        rightMargin=12 * mm,

        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )


    # =========================================================
    # STYLES
    # =========================================================

    styles = getSampleStyleSheet()


    system_style = ParagraphStyle(
        "HandoverSystem",
        parent=styles["Normal"],

        fontName="Helvetica-Bold",

        fontSize=11,
        leading=14,

        textColor=colors.HexColor(
            "#334155"
        ),

        spaceAfter=2 * mm,
    )


    title_style = ParagraphStyle(
        "HandoverTitle",
        parent=styles["Heading1"],

        fontName="Helvetica-Bold",

        fontSize=18,
        leading=22,

        textColor=colors.HexColor(
            "#0B716B"
        ),

        spaceAfter=4 * mm,
    )


    section_style = ParagraphStyle(
        "HandoverSection",
        parent=styles["Heading2"],

        fontName="Helvetica-Bold",

        fontSize=11,
        leading=14,

        textColor=colors.HexColor(
            "#0B716B"
        ),

        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )


    normal_style = ParagraphStyle(
        "HandoverNormal",
        parent=styles["Normal"],

        fontSize=8,
        leading=10,

        textColor=colors.HexColor(
            "#1E293B"
        ),
    )


    header_style = ParagraphStyle(
        "HandoverHeader",
        parent=normal_style,

        fontName="Helvetica-Bold",

        fontSize=8,
        leading=9,

        textColor=colors.HexColor(
            "#08766F"
        ),
    )


    # =========================================================
    # HELPERS
    # =========================================================

    def cell(value):

        if value is None or value == "":
            value = "-"

        return Paragraph(
            escape(str(value)),
            normal_style,
        )


    def header(value):

        return Paragraph(
            escape(str(value)),
            header_style,
        )


    # =========================================================
    # STORY
    # =========================================================

    story = []


    story.append(
        Paragraph(
            "Government Asset Information System",
            system_style,
        )
    )


    story.append(
        Paragraph(
            "Handover Record",
            title_style,
        )
    )


    story.append(
        Paragraph(
            "<b>Premise:</b> "
            + escape(selected_premise.name),
            normal_style,
        )
    )


    generated_date = timezone.localtime(
        timezone.now()
    ).strftime(
        "%d %B %Y"
    )


    story.append(
        Paragraph(
            "<b>Generated:</b> "
            + generated_date,
            normal_style,
        )
    )


    story.append(
        Paragraph(
            "<b>Generated By:</b> "
            + escape(
                request.user.get_full_name()
                or request.user.username
            ),
            normal_style,
        )
    )


    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )


    # =========================================================
    # 1. ASSET SUMMARY
    # =========================================================

    story.append(
        Paragraph(
            "1. Asset Summary",
            section_style,
        )
    )


    summary_data = [
        [
            header("Item"),
            header("Total"),
        ],

        [
            cell("Blocks / External Structures"),
            cell(block_count),
        ],

        [
            cell("Levels"),
            cell(level_count),
        ],

        [
            cell("Rooms / Open Areas"),
            cell(room_count),
        ],

        [
            cell("Asset Components"),
            cell(component_count),
        ],

        [
            cell("QR Labels"),
            cell(qr_count),
        ],
    ]


    summary_table = Table(
        summary_data,

        colWidths=[
            90 * mm,
            35 * mm,
        ],

        repeatRows=1,
    )


    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EAF7F5"
                    ),
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#DCE7E9"
                    ),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        summary_table
    )


    # =========================================================
    # 2. DOCUMENT SUMMARY
    # =========================================================

    story.append(
        Paragraph(
            "2. Document Summary",
            section_style,
        )
    )


    document_summary_data = [
        [
            header("Item"),
            header("Total"),
        ],

        [
            cell("Drawings"),
            cell(drawing_count),
        ],

        [
            cell("Documents"),
            cell(document_count),
        ],

        [
            cell("Outstanding Maintenance"),
            cell(outstanding_count),
        ],
    ]


    document_summary_table = Table(
        document_summary_data,

        colWidths=[
            90 * mm,
            35 * mm,
        ],
    )


    document_summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EAF7F5"
                    ),
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#DCE7E9"
                    ),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        document_summary_table
    )


    # =========================================================
    # 3. HANDOVER CHECKLIST
    # =========================================================

    story.append(
        Paragraph(
            "3. Handover Checklist",
            section_style,
        )
    )


    checklist_data = [
        [
            header("Item"),
            header("Status"),
        ],

        [
            cell("Premise Information"),
            cell("Complete"),
        ],

        [
            cell("Blocks / Structures"),
            cell(
                "Complete"
                if block_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Levels"),
            cell(
                "Complete"
                if level_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Rooms / Open Areas"),
            cell(
                "Complete"
                if room_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Asset Components"),
            cell(
                "Complete"
                if component_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("QR Labelling"),
            cell(
                "Complete"
                if qr_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Drawings"),
            cell(
                "Complete"
                if drawing_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Documents"),
            cell(
                "Complete"
                if document_count > 0
                else "Incomplete"
            ),
        ],

        [
            cell("Outstanding Maintenance"),
            cell(
                "Complete"
                if outstanding_count == 0
                else f"{outstanding_count} Item(s) Outstanding"
            ),
        ],
    ]


    checklist_table = Table(
        checklist_data,

        colWidths=[
            90 * mm,
            70 * mm,
        ],

        repeatRows=1,
    )


    checklist_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EAF7F5"
                    ),
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#DCE7E9"
                    ),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        checklist_table
    )


    # =========================================================
    # 4. DRAWINGS & DOCUMENTS REGISTER
    # =========================================================

    story.append(
        Paragraph(
            "4. Drawings & Documents Register",
            section_style,
        )
    )


    register_data = [
        [
            header("No."),
            header("Reference No."),
            header("Title"),
            header("Type"),
            header("Status"),
        ]
    ]


    register_number = 1


    for drawing in drawings:

        register_data.append(
            [
                cell(register_number),

                cell(
                    drawing.drawing_number
                ),

                cell(
                    drawing.title
                ),

                cell(
                    "Drawing"
                ),

                cell(
                    drawing.get_status_display()
                ),
            ]
        )

        register_number += 1


    for asset_document in documents:

        register_data.append(
            [
                cell(register_number),

                cell(
                    asset_document.document_number
                ),

                cell(
                    asset_document.title
                ),

                cell(
                    "Document"
                ),

                cell(
                    asset_document.get_status_display()
                ),
            ]
        )

        register_number += 1


    if register_number == 1:

        register_data.append(
            [
                cell("-"),
                cell("-"),
                cell(
                    "No drawings or documents registered."
                ),
                cell("-"),
                cell("-"),
            ]
        )


    register_table = Table(
        register_data,

        colWidths=[
            12 * mm,
            42 * mm,
            105 * mm,
            35 * mm,
            35 * mm,
        ],

        repeatRows=1,
    )


    register_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EAF7F5"
                    ),
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#DCE7E9"
                    ),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        register_table
    )


    # =========================================================
    # 5. OUTSTANDING MAINTENANCE
    # =========================================================

    story.append(
        Paragraph(
            "5. Outstanding Maintenance",
            section_style,
        )
    )


    maintenance_data = [
        [
            header("Request"),
            header("Asset / Location"),
            header("Issue"),
            header("Priority"),
            header("Status"),
            header("Assigned To"),
        ]
    ]


    for maintenance in outstanding_maintenance:

        # -----------------------------------------------------
        # LOCATION
        # -----------------------------------------------------

        if maintenance.component:

            location = (
                maintenance.component.component_id
                + " - "
                + maintenance.component.name
            )

        elif maintenance.room:

            location = (
                maintenance.room.room_tag
                + " - "
                + maintenance.room.name
            )

        elif maintenance.level:

            location = (
                maintenance.level.code
                + " - "
                + maintenance.level.name
            )

        elif maintenance.block:

            location = (
                maintenance.block.code
                + " - "
                + maintenance.block.name
            )

        else:

            location = (
                selected_premise.name
            )


        # -----------------------------------------------------
        # ASSIGNED
        # -----------------------------------------------------

        if maintenance.assigned_to:

            assigned_to = (
                maintenance.assigned_to.get_full_name()
                or maintenance.assigned_to.username
            )

        else:

            assigned_to = (
                "Not Assigned"
            )


        maintenance_data.append(
            [
                cell(
                    maintenance.request_no
                ),

                cell(
                    location
                ),

                cell(
                    maintenance.description
                ),

                cell(
                    maintenance.get_priority_display()
                ),

                cell(
                    maintenance.get_status_display()
                ),

                cell(
                    assigned_to
                ),
            ]
        )


    if outstanding_count == 0:

        maintenance_data.append(
            [
                cell("-"),

                cell("-"),

                cell(
                    "No outstanding maintenance requests."
                ),

                cell("-"),
                cell("-"),
                cell("-"),
            ]
        )


    maintenance_table = Table(
        maintenance_data,

        colWidths=[
            28 * mm,
            55 * mm,
            78 * mm,
            28 * mm,
            30 * mm,
            38 * mm,
        ],

        repeatRows=1,
    )


    maintenance_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#EAF7F5"
                    ),
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#DCE7E9"
                    ),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )


    story.append(
        maintenance_table
    )


    # =========================================================
    # 6. HANDOVER SIGN-OFF
    # =========================================================

    story.append(
        Paragraph(
            "6. Handover Sign-Off",
            section_style,
        )
    )


    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )


    signoff_data = [
        [
            cell("Prepared By"),
            cell("______________________________"),

            cell("Date"),
            cell("____________________"),
        ],

        [
            cell("Checked By"),
            cell("______________________________"),

            cell("Date"),
            cell("____________________"),
        ],

        [
            cell("Received By"),
            cell("______________________________"),

            cell("Date"),
            cell("____________________"),
        ],
    ]


    signoff_table = Table(
        signoff_data,

        colWidths=[
            30 * mm,
            70 * mm,
            20 * mm,
            55 * mm,
        ],
    )


    signoff_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )


    story.append(
        signoff_table
    )


    # =========================================================
    # BUILD PDF
    # =========================================================

    document.build(
        story
    )

    return response