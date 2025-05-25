## Permissions System Clarifications

This section provides further details on how the Knowledge Assistant's permissions system handles path specificity and access level hierarchies.

### Rule for Path Specificity

To ensure clear and unambiguous access control, the Knowledge Assistant employs a "most specific path takes precedence" rule when evaluating document permissions. This rule addresses potential conflicts that might arise when a document's location could seemingly fall under multiple path-based permissions.

**Core Principle:** The permission settings associated with the longest, most detailed (i.e., most specific) path to a document are the primary determinants of access.

**Example:**

Consider two defined paths and their associated permissions:

1.  `Docs/Staff/` (e.g., grants general access to all users with the "Staff" tag)
2.  `Docs/HR/Staff/` (e.g., grants access only to users with "Staff" tag *and* "HR" department affiliation)

If a document is located at `Docs/HR/Staff/employee_handbook.pdf`:

*   Access will be governed by the permissions set for `Docs/HR/Staff/`.
*   A user who only has general "Staff" access (derived from `Docs/Staff/`) but is *not* part of the "HR" department (and therefore doesn't qualify for `Docs/HR/Staff/` access) would **not** be able to access `Docs/HR/Staff/employee_handbook.pdf`.
*   Conversely, a user with "Staff" access *and* "HR" department affiliation would be granted access.

**General Tags vs. Specific Paths:**

While general tags (like "Staff" derived from a path like `Docs/Staff/`) apply broadly across documents matching that general path, they are overridden by more specific departmental or project tags if a document resides deeper within a more restrictive path. The system prioritizes the most granular permission set applicable to the document's exact location.

### Clarification of Access Levels (e.g., "Staff level and above")

Access levels within the Knowledge Assistant are designed to be hierarchical and generally inclusive upwards, providing a clear framework for managing document visibility based on roles or seniority.

**Core Principle:** Higher access levels typically encompass the permissions of lower access levels within the same contextual path (e.g., department, project).

**Standardized Wording and Interpretation:**

*   **Inclusive Upwards:** When a document or path is marked for a specific access level (e.g., "Staff" level within HR), users at that level *and any higher levels* within the same context (e.g., "Managers" and "Leads" within HR) will also have access.
*   **Example:** If a document at `Docs/HR/PerformanceReviews/staff_template.docx` is designated for "Staff" level access within HR:
    *   HR users with the "Staff" role can access it.
    *   HR users with the "Manager" role can access it.
    *   HR users with the "Lead" role can access it.
    *   Users outside of HR, regardless of their role, would not have access based on this rule alone (path specificity for HR would apply).

**Interaction with Folder Paths and Roles:**

The combination of folder paths and access level roles dictates final visibility:

*   **Accessing Deeper, More Restricted Levels:** A user must possess the required role (or higher) for a specific path. For example, documents in `Docs/HR/Management/strategic_plans.pdf` would typically require a user to have the "Management" role (or an equivalent or higher role like "Director") within the HR department.
*   **Accessing Broader, Less Restricted Levels:** Users with higher-level roles can generally access documents in subfolders intended for lower-level roles within their department/context. For instance, an HR Manager can view documents in `Docs/HR/Management/` (their designated level) as well as documents in `Docs/HR/Staff/`.
*   **Restriction for Lower Levels:** Conversely, someone with only the "Staff" role in HR would be able to see documents in `Docs/HR/Staff/` but would *not* be able to see documents in `Docs/HR/Management/` unless explicitly granted separate permissions.

**Reflecting in Pre-Filter (Step B):**

The "pre-filter" mechanism (Step B in the original document description) must consistently apply this hierarchical logic. When the system identifies a user's access level (e.g., "Manager" in "HR"), it should automatically include visibility to documents and paths designated for their level and any subordinate levels (e.g., "Staff" in "HR") within that same context. This ensures that searches and document listings accurately reflect a user's complete set of permissions based on their role and the defined hierarchy.
