resource "google_cloud_identity_group" "sandbox" {
  parent               = "customers/${var.customer_id}"
  display_name         = var.display_name
  initial_group_config = "WITH_INITIAL_OWNER"
  group_key {
    id = var.group_email
  }
  labels = {
    "cloudidentity.googleapis.com/groups.discussion_forum" = ""
  }
  lifecycle {
    prevent_destroy = true
    # initial_group_config is write-only: the API never returns it, so refresh
    # clears it from state and the plan reads ""->"WITH_INITIAL_OWNER" as a
    # ForceNew replacement, which prevent_destroy then blocks. Ignoring it keeps
    # existing groups (created or imported) stable across runs.
    ignore_changes = [initial_group_config]
  }
}

# Own only memberships declared in the approved request and this state.
# Pre-existing unmanaged memberships are not removed automatically.
resource "google_cloud_identity_group_membership" "member" {
  for_each = var.members
  group    = google_cloud_identity_group.sandbox.id
  preferred_member_key {
    id = each.value
  }
  roles {
    name = "MEMBER"
  }
}

output "group_name" {
  value = google_cloud_identity_group.sandbox.id
}
