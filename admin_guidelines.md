### **The Knowledge Assistant: Administrator's Guide**

Hello! This guide will walk you through managing the company's Knowledge Assistant. Your role is crucial to keeping the assistant smart, accurate, and secure.

Think of the Knowledge Assistant like a super-librarian. It reads all the documents you give it and helps employees find information. Your job is to be the **Head Librarian**, deciding which books go on which shelves and who is allowed in which sections of thelibrary.

This guide is split into two main jobs:
1.  **Managing the Documents** (The Library's Collection)
2.  **Managing the People** (The Library Cards)

---

### **Part 1: Managing the Documents (The Library's Collection)**

This is about adding, updating, or removing the files the assistant can read. All of our company documents are stored in a special shared folder called `sample_docs`. The way you name the folders inside `sample_docs` is very important—it's how you tell the assistant who is allowed to see what.

#### **The Golden Rule: Folder Names are Permission Tags**

The names of the folders act like labels on shelves in a library. They tell the assistant things like "This shelf is for the HR department" or "This shelf is for senior managers only."

Here are the types of "labels" you can use:

**1. Department Shelves:**
*   **What it does:** Restricts documents to members of a specific department (plus general users).
*   **How to use it:** Create a folder with an official department name.
*   **Examples:**
    *   `HR/`
    *   `IT/`
    *   `FINANCE/`

**2. Project Shelves:**
*   **What it does:** Organizes documents around a specific project.
*   **How to use it:** Create a folder with the project's name in all caps, like `PROJECT_NAME`.
*   **Examples:**
    *   `PROJECT_ALPHA/`
    *   `PROJECT_QUARTERLY_REVIEW/`

**3. Seniority Shelves (Hierarchy):**
*   **What it does:** Restricts documents to people at or above a certain seniority level.
*   **How to use it:** Create a folder name that includes the seniority level and a number.
    *   `STAFF_0_...` or `MEMBER_0_...` (Level 0: Everyone)
    *   `MANAGER_1_...` (Level 1: Managers and above)
    *   `EXECUTIVE_2_...` or `DIRECTOR_2_...` (Level 2: Executives and above)
    *   `BOARD_3_...` or `C_LEVEL_3_...` (Level 3: Top-level access only)
*   **Examples:**
    *   `STAFF_0_GUIDELINES/` (A folder for everyone)
    *   `MANAGER_1_REPORTS/` (A folder for managers)
    *   `BOARD_3_MEETING_MINUTES/` (A folder for the board)

**4. Special Role Shelves (Inside a Project or Department):**
*   **What it does:** Restricts documents to people who have a specific job title *within* a project or department.
*   **How to use it:** Inside a Project or Department folder, create a sub-folder with a special name.
    *   `lead_docs/` (For people with the "LEAD" role)
    *   `admin_files/` (For people with the "ADMIN" role)
    *   `manager_exclusive/` (For people with the "MANAGER" role)
*   **Example:**
    *   To give only the Project Lead of Project Alpha access to a file, you would place it here: `PROJECT_ALPHA/lead_docs/secret_plan.pdf`

#### **Putting It All Together: Your Daily Tasks**

**To Add a New Document:**
1.  Figure out who needs to see the document. Is it for a specific department? A certain seniority level?
2.  Navigate inside the `sample_docs` folder.
3.  Find the folder that matches the permissions you need. If it doesn't exist, create it following the naming rules above.
4.  Copy the new document into that folder.
5.  **Important:** The assistant will automatically find and learn from the new document overnight.

**To Update a Document:**
1.  Find the document you want to update inside `sample_docs`.
2.  Replace it with the new version (you can just copy and paste the new file over the old one).
3.  The assistant will automatically see the change and learn the new information overnight.

**To Remove a Document:**
1.  Find the document inside `sample_docs` and simply delete it.
2.  The assistant will automatically notice it's gone and will "forget" it overnight.

---

### **Part 2: Managing the People (The Library Cards)**

This is about controlling who has access to what information. You will do all of this using the **Admin Panel** in the Knowledge Assistant web application.

**How to get there:**
1.  Log in with your special Admin account.
2.  You will see a "Show Admin Panel" button. Click it.

The Admin Panel has three main sections.

#### **Section 1: Viewing a User's Permissions**

*   **When to use:** When you want to check what "library card" someone has.
*   **Steps:**
    1.  Go to the "View User Permissions" section.
    2.  Type the user's full work email into the box.
    3.  Click the "View Permissions" button.
    4.  A box will appear showing you their current seniority level, departments, projects, and special roles.

#### **Section 2: Changing a User's Permissions (or Creating a New User)**

This is your most powerful tool. You can grant access, change it, or even create an account for a new employee.

*   **Steps:**
    1.  Go to the "Manage User Permissions" section.
    2.  **Target User Email:** Type in the email of the person you want to manage. **If they don't have an account yet, this will create one for them.**
    3.  **New Hierarchy Level:** To change their seniority, enter a number (0 for Staff, 1 for Manager, 2 for Executive, 3 for Admin/Board). *Leave this blank if you don't want to change it.*
    4.  **Departments:** To add someone to one or more departments, type the department names separated by a comma (e.g., `HR,IT`). *Leave blank for no change.*
    5.  **Projects:** To add someone to projects, type the project names separated by a comma (e.g., `PROJECT_ALPHA,PROJECT_BETA`). *Leave blank for no change.*
    6.  **Contextual Roles (Special Jobs):** This is for giving someone a special role *within* a project or department.
        *   In the "Context" box, type the Project or Department name (e.g., `PROJECT_ALPHA`).
        *   In the "Role Name" box, type the role you want to give them (e.g., `LEAD`, `AI_ENGINEER`, `FRONTEND_DEV`).
        *   Click "Add Role". You can do this multiple times for different roles.
        *   **Warning:** When you submit, this will replace *all* of the user's old roles. You are setting their new complete list of roles.
    7.  Click the **"Update User Permissions"** button. A success message will appear.

#### **Section 3: Removing a User**

*   **When to use:** When an employee leaves the company. This will completely remove their access.
*   **Steps:**
    1.  Go to the "Remove User" section.
    2.  Carefully type the full email of the user you want to remove.
    3.  Click the "Remove User" button.
    4.  A confirmation box will pop up. This is a permanent action, so be sure! Click "OK".
    5.  The user's account and all their access will be deleted.

---

That's it! By managing the **folder names** and the **user permissions** in the Admin Panel, you have complete control over the Knowledge Assistant. If you ever have a question, just remember the library analogy: you are organizing the shelves and managing the library cards.