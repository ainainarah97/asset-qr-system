def apply_sorting(
    queryset,
    request,
    allowed_sort,
):
    sort = request.GET.get(
        "sort"
    )

    if sort in allowed_sort:

        queryset = queryset.order_by(
            allowed_sort[sort]
        )

    return queryset