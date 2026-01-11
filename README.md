# Teaching Record Hub

The Teaching Record Hub is a Django-based web application designed for educational institutions to streamline the process of managing and analyzing teaching records. It allows lecturers to upload their teaching data via structured Excel files, and provides administrators with tools to manage users and view system-wide analytics.

## Technology Stack

The application employs a modern, server-rendered architecture with targeted client-side enhancements.

### Backend Technologies

*   **Framework:** [Django](https://www.djangoproject.com/) serves as the core backend framework, handling routing, business logic, database interactions, and user authentication.
*   **Database:** SQLite is used as the default database, suitable for development and small-to-medium scale deployment. The architecture allows for easy swapping to other databases like PostgreSQL.
*   **Data Processing:** The powerful [pandas](https://pandas.pydata.org/) library is the engine for data analysis. It reads, cleans, and processes data from uploaded Excel files.
*   **Excel File Support:** `openpyxl` and `pyxlsb` are used to provide broad support for both modern (`.xlsx`) and binary (`.xlsb`) Excel formats.
*   **PDF/Excel Reporting:** User-facing reports are generated on-the-fly using [reportlab](https://www.reportlab.com/) for PDFs and `openpyxl` for native Excel files.

### Frontend Technologies & Architecture

The frontend follows a traditional server-rendered model, where Django's template engine generates the HTML for the browser. This is enhanced with JavaScript for dynamic client-side interactivity. **Note:** This project does not use HTMX.

*   **Templating:** Standard [Django Templates](https://docs.djangoproject.com/en/stable/topics/templates/), which share a similar syntax with Jinja, are used to render dynamic HTML content on the server.
*   **Styling:** [TailwindCSS](https://tailwindcss.com/) is used via a CDN to provide a modern, utility-first CSS framework for rapid UI development.
*   **Client-Side Interactivity:**
    *   **Vanilla JavaScript:** A dedicated `teaching_records.js` file handles major interactive features like tab switching, form submissions, and DOM manipulation.
    *   **[Alpine.js](https://alpinejs.dev/):** This lightweight JavaScript framework is "sprinkled" into the HTML to manage small, isolated components with declarative attributes. For example, it powers UI elements like dropdown menus, managing their state (open/closed) directly in the HTML without needing a full-page reload.

This hybrid approach allows for robust server-side rendering from Django while providing a responsive and modern user experience through targeted use of Alpine.js and vanilla JavaScript.

## Core Features

### For Lecturers:
*   **Secure Registration & Login:** Lecturers can register for an account, which requires administrator approval before activation.
*   **Dashboard:** A personalized dashboard displaying key statistics, charts on weekly hours, and upcoming sessions.
*   **File Upload:** Easily upload teaching records using a predefined `.xlsb` Excel template. The system intelligently parses the file to extract and validate data.
*   **Teaching Records Management:** View, search, filter, and sort all teaching sessions in a detailed table.
*   **Workload Analysis:** Get a clear overview of teaching workload, broken down by various metrics.
*   **Data Export:** Export teaching records in multiple formats, including CSV, PDF, and XLSX for further analysis or reporting.
*   **Customizable Experience:** Personalize the application theme (light/dark mode), date format, and the columns visible in the records table.

### For Administrators:
*   **User Management:** A dedicated dashboard to view all registered lecturers.
*   **Approval Workflow:** Approve or deactivate lecturer accounts to control system access.
*   **System Oversight:** (Future capability) Access to system-wide analytics and reporting.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd teaching-record-hub
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run database migrations:**
    ```bash
    python teaching_analytics/manage.py migrate
    ```

5.  **Create a superuser (administrator):**
    ```bash
    python teaching_analytics/manage.py createsuperuser
    ```

6.  **Run the development server:**
    ```bash
    python teaching_analytics/manage.py runserver
    ```
    The application will be available at `http://127.0.0.1:8000`.

## Usage

1.  **Admin:** Log in with the superuser credentials to access the admin dashboard, manage users, and approve new lecturer registrations.
2.  **Lecturer:** Register a new account. Once approved by an admin, you can log in to upload your teaching files, view your dashboard, and manage your records.