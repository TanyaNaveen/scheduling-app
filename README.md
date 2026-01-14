# Worship Team Scheduler

An application for generating optimized worship team schedules using integer/constraint programming (Google OR-Tools).

The app collects data from users, is integrated with a PostgreSQL database (Supabase), and builds a scheduling optimization model. It generates one or more feasible schedules, and allows admins to review, edit, compare, and export schedules.

The eventual goal for this project is to build a maintainable, self-contained application to be used by the student leadership team for RUF, a registered student organization at the University of Washington. 
Students should be able to use this to generate quarterly worship team schedules, and use this tool for other general-purpose scheduling tasks as well. 

---
## Optimization Model (High-Level)

The scheduler enforces:

* Availability constraints
* Instrument capability constraints
* Leadership requirements
* Frequency targets (soft constraints with penalties)
* Optional preference weights (instrument or combination-based)

The model is built using OR-Tools CP-SAT and can return multiple feasible solutions.

---

## Tech Stack

* **Python 3.10+**
* **Streamlit** (UI)
* **Supabase** (DB)
* **pandas** (data manipulation)
* **Google OR-Tools** (constraint solver)

---

## Roadmap and Todos

[1/14/2026] The user-facing form and data collection is fully functional. Admin portal in progress.
