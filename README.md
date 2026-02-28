# Annebrato

This repository contains a minimal website and text‑based troubleshooting guide
intended for use by an IT professional on a mobile device (e.g. via Termux).
The site is served by a simple Python HTTP server and displays the contents of a
plain text file. You can edit the file on the device and the changes appear in
the browser when refreshed.

## Usage

1. Install Python 3 on your device (Termux: `pkg install python`).
2. Clone or copy this repository onto the mobile device.
3. Navigate to the repository directory and run:
   ```sh
   python3 server.py
   ```

   The server will also serve a simple CSS file (`style.css`) to make the
   page easier to read. Feel free to modify or replace it with your own styles.
4. In a browser on the same device (or another on the local network) visit:
   `http://<device-ip>:8000/` (or `http://localhost:8000` if local).
5. Edit `steps.txt` with any text editor to add or modify troubleshooting steps.
   Use **application headings** to categorize issues – start a line with
   `# Application Name` and then list steps below it. The web page will show a
   dropdown letting you filter by each application ("All applications" shows
   everything). Example:

   ```text
   # Opera PMS
   - check service
   # Veeam
   - review job logs
   ```

   Save the file and refresh the browser to see the updates and filtering UI.

   A **search box** appears at the top of the page. Type any term and the
   displayed sections will be narrowed to those containing the text. When a
   match is found only the specific lines (errors, steps, paragraphs) that
   include the term are shown; unrelated content within the same section is
   hidden. You can combine the search with the application dropdown to further
   narrow the results.

6. **Formatting and Editing**

   The server understands simple Markdown-like syntax and displays each
   heading as a separate, filterable section. The card-style layout has been
   removed in favor of plain sections.
   - `# Application Name` defines a new section (as before).
- Sub‑headings (`##`, `###`) will render as `<h3>`/`<h4>` within each section.
   - Start lines with `- ` to create bullet lists; **bold text** using `**text**`.
   - Paragraphs are automatically wrapped in `<p>` tags.

   You can also edit content directly in your browser. Visit
   `http://<device-ip>:8000/editor` to add new applications or modify the whole
   guide without a text editor. Choose between:
   - Quick add: Provide application name and initial steps.
   - Full editor: Edit the entire `steps.txt` file and save.

   Additional features:
   - **Live search** filters sections and displays only matching lines; terms
     are highlighted. Typing a few characters also shows a dropdown of matching
     applications/snippets you can click to jump directly to that section.
   - Sections can be collapsed/expanded individually or via "Collapse all" /
     "Expand all" buttons.
   - Dark mode toggle (🌙) persists your preference.
   - A sticky header keeps controls visible while scrolling; back‑to‑top button
     appears when you scroll down.
   - The page shows when the underlying text file was last modified.
   - Performance is improved with in‑memory caching of parsed sections.
   - Print stylesheet hides controls and formats the content cleanly.

## Content Included

The site comes pre-populated with comprehensive troubleshooting for:

- **Opera PMS** – Service startup, UI/performance, printer setup, database,
  guest accounts, network issues.
- **Opera OXI / Pegasus Errors** – Complete error reference from Oracle official
  documentation; covers parsing errors, reservation issues, room/inventory
  problems, and external system connectivity.
- **Outlook Mail** – Memory/performance optimization, mailbox sizing, archiving
  best practices, email sync, permissions, attachments, encryption, add-ins.
- **Veeam Backup & Replication** – Installation, job configuration, failure
  troubleshooting, repository/storage, restore operations, proxy setup,
  credentials, database, tape and cloud backup.
- **Onity Server** – Installation, lock communication, card encoding, database
  integrity, network, user management, access troubleshooting, firmware.
- **Internet Connectivity** – Basic checks, network configuration, Wi-Fi issues,
  firewall/security, DNS, bandwidth/latency, VPN.
- **Windows Commands** – Network diagnostics, system repair, processes, file
  operations, disk management, user accounts, registry, updates.
- **POS Terminal Errors & Products** – Common error codes (100, 200, 300, etc.),
  connection issues, card declines, printer faults, system timeouts, plus
  device features and troubleshooting tips.

Only you should access the site; it is an unauthenticated, local‑network server.

