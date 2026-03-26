from berryllium.mods.models import Mod, ModFile, ModFileGroup
from berryllium.mods.forms import ModFileGroupForm, ModFileForm
from berryllium.mods.services import (
    create_file_group,
    update_file_order,
    update_filegroup_order,
    swap_order,
)

from django.shortcuts import render, HttpResponse, redirect
from django.views.decorators.http import require_POST, require_GET
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


@require_POST
def hx_process_url_field(request):
    """HTMX endpoint to validate file URL field."""
    file_url = request.POST.get("file_url", "")
    mod_id = request.session.get("session_id")

    # shouldn't really happen unless session is lost
    if not mod_id:
        return HttpResponse(status=400)

    mod = Mod.objects.filter(id=mod_id).first()
    # save url field when cleared
    if not file_url:
        if mod:
            mod.external_url = ""
            mod.is_external = False
            mod.save()
        # return empty response to clear any existing errors
        return HttpResponse()

    # handle dynamic validation
    try:
        URLValidator(schemes=["http", "https"])(file_url)
    except ValidationError:
        error_message = (
            "Please enter a valid URL. Protocol (http:// or https://) is required."
        )
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": error_message},
        )

    # if valid, save to mod draft
    if mod:
        mod.external_url = file_url
        mod.is_external = True
        mod.save()

    # if valid, return empty response
    return HttpResponse()


@require_POST
def hx_toggle_group_manager(request):
    """HTMX endpoint to toggle file group manager visibility."""
    isToggled = "group_manager_toggle" in request.POST
    request.session["group_manager_toggled"] = isToggled
    return HttpResponse()


@require_POST
def hx_validate_filegroup_name(request, fg_id):
    """HTMX endpoint to validate filegroup name field."""
    groupname = request.POST.get("form-" + str(fg_id) + "-name", "").strip()
    print("Received group name for validation:", groupname, "for ModFileGroup ID:", fg_id)

    form = ModFileGroupForm(data={"name": groupname}, instance=ModFileGroup(id=fg_id))
    form.is_valid()

    errors = form.errors.get("name", [])
    if errors:
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": errors[0]},
        )

    # if valid, save to ModFileGroup draft
    file_group = ModFileGroup.objects.filter(id=fg_id).first()
    if file_group:
        file_group.name = groupname
        file_group.save()

    return HttpResponse()


@require_POST
def hx_validate_filegroup_description(request, fg_id):
    """HTMX endpoint to validate filegroup description field."""
    print("Validating description for ModFileGroup ID:", fg_id)
    description = request.POST.get("form-" + str(fg_id) + "-description", "").strip()

    form = ModFileGroupForm(
        data={"description": description}, instance=ModFileGroup(id=fg_id)
    )
    form.is_valid()

    errors = form.errors.get("description", [])
    if errors:
        print(
            "Validation errors for ModFileGroup ID:",
            fg_id,
            "Description:",
            description,
            "Errors:",
            errors,
        )
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": errors[0]},
        )

    # if valid, save to ModFileGroup draft
    file_group = ModFileGroup.objects.filter(id=fg_id).first()
    print("Saving description for ModFileGroup ID:", fg_id, "Description:", description)
    if file_group:
        file_group.description = description
        print("Saved description for ModFileGroup ID:", fg_id)
        file_group.save()

    return HttpResponse()


@require_POST
def hx_validate_singlefile_title(request, file_id):
    """HTMX endpoint to validate single file title field."""
    title = request.POST.get("fileform-" + str(file_id) + "-title", "").strip()
    print("Received title for validation:", title, "for ModFile ID:", file_id)

    # not a form.ModelForm so we can validate with a regular form and save to ModFile instance
    form = ModFileForm(data={"title": title})
    form.is_valid()

    errors = form.errors.get("title", [])
    print(
        "Validating title for ModFile ID:",
        file_id,
        "Title:",
        title,
        "Errors:",
        errors,
    )
    if errors:
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": errors[0]},
        )

    # if valid, save to ModFile draft
    file_upload = ModFile.objects.filter(id=file_id).first()
    if file_upload:
        file_upload.title = title
        file_upload.save()

    return HttpResponse()


@require_POST
def hx_validate_singlefile_description(request, file_id):
    """HTMX endpoint to validate single file description field."""
    description = request.POST.get(
        "fileform-" + str(file_id) + "-description", ""
    ).strip()

    form = ModFileForm(data={"description": description})
    form.is_valid()

    errors = form.errors.get("description", [])
    if errors:
        return render(
            request,
            "mods/upload/step/partials/hx_errors.html",
            {"error_message": errors[0]},
        )

    # if valid, save to ModFile draft
    file_upload = ModFile.objects.filter(id=file_id).first()
    if file_upload:
        file_upload.description = description
        file_upload.save()

    return HttpResponse()


@require_POST
def hx_add_filegroup_form(request):
    """HTMX endpoint to add a new file group form."""

    mod_id = request.session.get("session_id")
    if not mod_id:
        return HttpResponse(status=400)

    # ------------ Create new ModFileGroup instance for the new form
    ModFileGroup.objects.create(
        mod_id=mod_id,
        name="New Group",
        order=ModFileGroup.objects.filter(mod_id=mod_id).count(),
    )

    # ------------ Rebuild context and file group data for re-rendering
    file_group_forms, filegroups, group_formset = create_file_group(mod_id)

    # ------------ Re-render
    return render(
        request,
        "mods/upload/step/partials/group_filegroup.html",
        {"group": group_formset.forms[-1], "file_groups": filegroups},
    )


@require_POST
def hx_remove_filegroup_form(request, fg_id):
    """HTMX endpoint to remove a file group form."""
    print("Attempting to delete ModFileGroup with ID:", fg_id)
    ModFileGroup.objects.filter(id=fg_id).delete()
    update_filegroup_order(request.session.get("session_id"))
    return HttpResponse()


@require_POST
def hx_add_file_to_group(request):
    """HTMX endpoint to add a file to a file group after drag/drop."""
    file_id = request.POST.get("dragged_id")
    fg_id = request.POST.get("fg_id")
    new_index = int(request.POST.get("new_index"))
    print("Adding file ID", file_id, "to ModFileGroup ID", fg_id, "at index", new_index)
    file = ModFile.objects.filter(id=file_id).first()
    group = ModFileGroup.objects.filter(id=fg_id).first()
    previous_group = file.filegroup if file else None

    if not file or not group:
        return HttpResponse(status=400)

    # re-assign file to new group
    file.filegroup = group
    file.save()

    update_file_order(group, moved_file=file, index=new_index)
    if previous_group:
        update_file_order(previous_group)

    # empty response
    return HttpResponse(status=204)


@require_POST
def hx_update_file_order_in_group(request):
    """Update the order of files in a group after drag/drop."""
    fg_id = request.POST.get("fg_id")
    old_index = request.POST.get("old_index")
    new_index = request.POST.get("new_index")
    print(
        "Updating file order in ModFileGroup ID",
        fg_id,
        "Old Index:",
        old_index,
        "New Index:",
        new_index,
    )

    group = ModFileGroup.objects.filter(id=fg_id).first()
    if not group:
        return HttpResponse(status=400)

    file = ModFile.objects.filter(filegroup=group).order_by("order")[int(old_index)]
    update_file_order(group, moved_file=file, index=int(new_index))

    return HttpResponse(status=204)


@require_GET
def hx_empty_filegroups_warning(request):
    """HTMX endpoint to check for empty file groups before proceeding to next step."""
    print("Checking for empty file groups for mod in session.")
    mod_id = request.session.get("session_id")
    if not mod_id:
        print("No mod_id in session when checking for empty file groups.")
        return HttpResponse(status=400)

    empty_groups_count = ModFileGroup.objects.filter(
        mod_id=mod_id, files__isnull=True
    ).count()
    print(
        "Checking for empty file groups. Mod ID:",
        mod_id,
        "Empty Groups Count:",
        empty_groups_count,
    )
    if empty_groups_count > 0:
        return render(
            request,
            "mods/upload/step/partials/group_empty_modal.html",
            {"empty_group_len": empty_groups_count},
        )

    return HttpResponse(status=204)


@require_POST
def hx_remove_empty_filegroups(request):
    """HTMX endpoint to remove a file from a file group (drag to ungroup)."""
    mod_id = request.session.get("session_id")
    if not mod_id:
        print("No mod_id in session when checking for empty file groups.")
        return HttpResponse(status=400)

    empty_groups = ModFileGroup.objects.filter(mod_id=mod_id, files__isnull=True)
    print(f"After a search, found {empty_groups.count()} empty file groups.")
    if not empty_groups.exists():
        print("No empty file groups found for mod ID:", mod_id)
        return HttpResponse(status=400)

    for group in empty_groups:
        group.delete()

    # update order
    update_filegroup_order(mod_id)

    return redirect("upload_step3")


@require_POST
def hx_move_filegroup_up(request, current_index):
    """HTMX endpoint to move a file group up in the order."""
    mod_id = request.session.get("session_id")
    if not mod_id:
        return HttpResponse(status=400)

    groups = list(ModFileGroup.objects.filter(mod_id=mod_id).order_by("order"))

    # swap order with the previous group
    swap_order(groups, current_index, "up")

    return redirect("mod_create_step2")


@require_POST
def hx_move_filegroup_down(request, current_index):
    """HTMX endpoint to move a file group down in the order."""
    mod_id = request.session.get("session_id")
    if not mod_id:
        return HttpResponse(status=400)

    groups = list(ModFileGroup.objects.filter(mod_id=mod_id).order_by("order"))

    # swap order with the next group
    swap_order(groups, current_index, "down")

    return redirect("mod_create_step2")
