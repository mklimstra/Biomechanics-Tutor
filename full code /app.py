from shiny import App, reactive, render, ui
import pandas as pd
import random
from pathlib import Path
from starlette.staticfiles import StaticFiles
import asyncio  # minimal functional addition for first-load delay

# Helper function to sanitize section names for button IDs
def sanitize_id(name):
    return ''.join(c if c.isalnum() else '_' for c in name)

# Get the current directory and construct path to CSV
current_dir = Path(__file__).parent
csv_path = current_dir / "Master_questions.csv"

# Load and process the data
df = pd.read_csv(csv_path, encoding="utf-8-sig")
df["correct_option"] = (
    pd.to_numeric(df["correct_option"], errors="coerce")
      .astype("Int64")   # capital “I” — pandas’ nullable integer
)
# drop any nan section values
sections = (
    df["section"]
      .dropna()        # remove NaN
      .astype(str)     # ensure every entry is a string
      .unique()
      .tolist()
)
# Store the ID of the last shown notification (so we can remove it if a new one appears)
last_notification_id = reactive.Value(None)

# Track whether app is on its initial load
initial_load = reactive.Value(True)

# **Reactive Value to Track Section Selection**
is_section_selected = reactive.Value(False)

# **Landing Page UI Component**
landing_page_ui = ui.page_fluid(
    ui.div(
        ui.h1("Welcome to the Biomechanics Tutor", class_="welcome-title"),
        ui.p("Please select a section to begin:", class_="welcome-subtitle"),
        # **Dynamic Section Buttons**
        ui.div(
            [
                ui.input_action_button(
                    f"section_button_{sanitize_id(section)}",
                    section,
                    class_="section-button",
                )
                for section in sections 
            ],
            class_="section-buttons-container",
            style="""
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 20px;
                width: 80%;
                max-width: 600px;
                margin-top: 30px;
            """,
        ),
        class_="landing-container",
        style="""
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            background-color: #ffffff;
        """,
    )
)

# **Combined UI with Conditional Rendering**
app_ui = ui.page_fluid(
    ui.output_ui("main_ui"),
    ui.tags.head(
        # Include KaTeX and Marked.js for client-side rendering
        ui.tags.link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css",
        ),
        ui.tags.script(
            src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"
        ),
        ui.tags.script(
            src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
        ),
        ui.tags.script(
            src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"
        ),
        ui.tags.script(
            # Minimal functional change: second pass ensures markdown-only (no KaTeX) renders
            """
            function renderContent(selector) {
                setTimeout(function() {
                    try {
                        const elems = document.querySelectorAll(selector);
                        elems.forEach(function(elem) {
                            const markdownText = elem.getAttribute('data-markdown');
                            if (markdownText !== null) {
                                const html = marked.parse(markdownText);
                                elem.innerHTML = html;
                            }
                        });
                        // After parsing markdown, render math
                        renderMathInElement(document.body, {
                            delimiters: [
                                {left: "$$", right: "$$", display: true},
                                {left: "$", right: "$", display: false}
                            ],
                            throwOnError: false
                        });
                    } catch (error) {
                        console.error("Error in renderContent:", error);
                    }
                }, 50);
            }
            Shiny.addCustomMessageHandler('render-math', function(message) {
                renderContent(message.selector);
                // extra pass for non-math questions
                setTimeout(function(){ renderContent(message.selector); }, 150);
            });
            """
        ),
        # Script to collapse the nav on custom message (hamburger toggler)
        ui.tags.script(
            """
            Shiny.addCustomMessageHandler('collapse-navbar', function(message) {
                var toggler = document.querySelector('.navbar-toggler');
                if (toggler && window.getComputedStyle(toggler).display !== 'none') {
                    toggler.click();
                }
            });
            """
        ),
    ),
    ui.tags.style(
        """
        /* ---------------- GLOBAL LAYOUT / BODY ----------------
           Controls overall page background and margin */
        body {
            background-color: #e0e0e0 !important; /* Gray background */
            margin: 0 !important;                /* Remove default page margin */
        }

        /* ---------------- NAVBAR ----------------
           The top bar. Fixed at top, full width, high z-index */
        .navbar {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            z-index: 9999 !important;
        }

        /* ---------------- NOTIFICATIONS ----------------
           Appear ~50px from top, aligned to right */
        .shiny-notification {
            position: fixed !important;
            top: 50px !important;
            right: 10px !important;
            bottom: auto !important;
        }

        /* ---------------- TITLE CONTAINER ----------------
           For the main page title. 
           .title-container is used in navset_bar "title" */
        .title-container {
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            background-color: #f8f9fa !important; /* Light gray background */
        }

        /* ---------------- #combined_answer ----------------
           Displays the numeric+units text. Slightly bigger font, 
           aligned vertically */
        #combined_answer {
            color: #6c757d;
            font-weight: 500;
            font-size: 1.1em;
            padding: 6px 0 !important;
            margin: 0 !important;
            border-top: none !important;
            display: flex !important;
            align-items: center !important;
            height: 100% !important;
        }

        /* ---------------- SELECTIZE / FORM CONTROLS ----------------
           Minimizes extra space on selectize controls and form fields */
        .selectize-control {
            min-width: 100px !important;
            max-width: 100% !important;
            margin: 0px !important;
            padding: -20px -10px !important; /* Negative padding to reduce space */
        }
        .selectize-dropdown, .selectize-input, .selectize-input input {
            padding: -20px -10px !important;
            margin: 0px !important;
        }
        .form-control {
            max-width: 100% !important;
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            padding: -20px -10px !important;
        }
        .form-control, .selectize-control {
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            padding: -20px -10px !important;
        }

        /* 
           .col-4, .col-8, .col-12 
           Adjust column spacing to be minimal 
        */
        .col-8, .col-4, .col-12 {
            padding: 4px !important;
            margin: 0 !important;
        }

        /* ---------------- QUESTION BANNER ----------------
           The banner at the top of each question card */
        .question-banner {
            background-color: #ffffff;
            border-radius: 8px 8px 0 0;
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            padding: -10px 0px !important;
            border-bottom: 0px solid #ffffff;
        }
        .question-banner2 {
            background-color: #ffffff;
            border-radius: 8px 8px 0 0;
            margin-top: 0px !important;
            margin-bottom: 0px !important;
            padding: -10px 0px !important;
            border-bottom: 0px solid #ffffff;
        }

        /* ---------------- CARD CONTENT ----------------
           .card > div => add consistent left/right padding inside the card */
        .card > div {
            padding-left: 20px !important;
            padding-right: 20px !important;
        }

        /* ---------------- QUESTION TITLE ----------------
           The heading text inside .question-banner */
        .question-title {
            color: #333;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 600;
            font-size: 20px;
            letter-spacing: 0.5px;
            text-transform: none;
            margin-top: -15px !important;
            margin-bottom: -20px !important;
            padding: 6px 0;
        }
        .question-title2 {
            color: #333;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 600;
            font-size: 20px;
            letter-spacing: 0.5px;
            text-transform: none;
            margin-top: -5px !important;
            margin-bottom: -20px !important;
            padding: 6px 0;
        }

        /* ---------------- MAIN PAGE TITLE (TUTOR-TITLE) ----------------
           The top-level title in the navset_bar "title" */
        .tutor-title {
            color: #333;
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-weight: 600;
            font-size: 28px;
            letter-spacing: 0.5px;
            text-transform: none;
            margin: 0;
            padding: 0;
        }

        /* ---------------- PRIMARY BUTTONS ----------------
           e.g. "Submit Answer" */
        .btn-primary {
            background-color: #007bff;
            border: 1px solid #007bff;
            color: #ffffff;
            padding: 12px 10px;
            border-radius: 6px;
            transition: all 0.3s ease;
            width: 100%;
            margin: 0 !important;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: none;
            cursor: pointer;
        }
        .btn-primary:hover {
            border-color: #0056b3;
            color: #0056b3;
            background-color: #ffffff;
        }
        .btn-primary:active {
            background-color: #ffffff;
            border-color: #007bff;
            color: #007bff;
        }

        /* ---------------- OPTION BUTTON ----------------
           For multiple-choice cards */
        .option-button {
            transition: all 0.3s ease;
            border: 1px solid #6c757d !important;
            background-color: #ffffff !important;
            padding: 0 !important;
            margin: 0 !important;
            border-radius: 8px !important;
            width: 100% !important;
            height: 100% !important;
            display: block !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            color: #333 !important;
            cursor: pointer;
        }
        .option-button:hover {
            border-color: #007bff !important;
            color: #007bff !important;
            background-color: #ffffff !important;
        }

        /* 
           Inline images inside .card 
           -> margin top/bottom, side padding
        */
        .card img {
            margin: 10px 0 25px 0;
            padding: 0 20px;
        }

        /* ---------------- QUESTION STEPS (NAV-PILLS) ---------------- 
           For steps inside main_content => .nav-pills, etc. */
        .question_steps {
            padding: 0 !important;
            margin: 0 !important;
        }
        .question_steps .nav-pills {
            margin-top: 0 !important;
            margin-bottom: 10px !important;
            padding-left: 0px !important;
            background: none !important;
            row-gap: 10px;
        }
        .question_steps .nav-pills .nav-link {
            color: #ffffff;
            background-color: #007bff;
            border: 1px solid #007bff;
            margin-right: 8px;
            border-radius: 6px;
            padding: 10px 25px;
            transition: all 0.2s ease;
            font-weight: 500;
            min-width: 100px;
            text-align: center;
        }
        .question_steps .nav-pills .nav-link:hover {
            border-color: #0056b3;
            color: #0056b3;
            background-color: #ffffff;
        }
        .question_steps .nav-pills .nav-link.active {
            border-color: #007bff;
            color: #007bff;
            background-color: #ffffff;
        }
        .question_tabs {
            margin-bottom: 5px;
        }

        /* ---------------- NAV-TABS (QUESTION NAV) ----------------
           For .question_nav => .nav-tabs */
        .nav-tabs {
            margin-top: 25px;
            margin-bottom: 10px;
            background: none !important;
            border-bottom: none !important;
            row-gap: 10px;
            padding-left: 0px !important;
        }
        .nav-tabs .nav-link {
            color: #ffffff;
            background-color: #007bff;
            border: 1px solid #007bff;
            margin-right: 4px;
            border-radius: 6px;
            padding: 8px 20px;
            transition: all 0.2s ease;
            font-weight: 500;
        }
        .nav-tabs .nav-link:hover {
            border-color: #0056b3;
            color: #0056b3;
            background-color: #ffffff;
        }
        .nav-tabs .nav-link.active {
            border-color: #007bff;
            color: #007bff;
            background-color: #ffffff;
        }

        /* ---------------- CARD STYLING ----------------
           Used for question_card, main_content, etc. */
        .card {
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            position: relative !important;
            padding: 0 !important;
        }
        .card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .card .row {
            margin-top: 0px;
            margin-bottom: 0px;
            padding: 0;
        }
        .option-button-card {
            padding: 0 !important;
            overflow: hidden !important;
            height: 100% !important;
            position: relative !important;
            min-height: 100px !important;
        }
        .option-button > div {
            position: absolute !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: 100% !important;
            padding: 15px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }
        .option-button .markdown-content {
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }

        /* ---------------- ANSWER CONTENT ----------------
           For the row that contains numeric input, units, combined answer, etc. */
        .answer-content .row {
            margin: 0 !important;
            padding: 8px !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
        }

        /* 
           Additional form-group / selectize spacing 
        */
        .form-group {
            margin: 0 !important;
            padding: 0 !important;
        }
        .form-control, .selectize-control {
            margin: 0 !important;
            padding: 6px !important;
        }
        input[type="number"] {
            width: 100% !important;
            min-width: 80px !important;
        }
        #combined_answer {
            margin: 0 !important;
            padding: 4px 5px !important;
        }

        /* ---------------- MARKDOWN / QUESTION TEXT ----------------
           For question bodies, solutions, etc. */
        .markdown-base {
            margin-top: -10px;
            font-family: 'Helvetica Neue', Arial, sans-serif !important;
            font-size: 1.1em !important;
            margin-bottom: 0px;
            padding: 0 -10px;
            color: #333 !important;
        }
        .main-question-content {
            margin-top: 25px;
            font-family: 'Helvetica Neue', Arial, sans-serif !important;
            font-size: 1.1em !important;
            margin-bottom: 10px;
            padding: -10px 10px;
            color: #333 !important;
        }
        .markdown-content {
            margin-top: 0px;
            padding: 0px -10px !important;
            font-family: 'Helvetica Neue', Arial, sans-serif !important;
            font-size: 1.1em !important;
            line-height: 1.6 !important;
            color: #333 !important;
        }
        .solution-markdown-content {
            margin-top: 20px;
            padding: 0px -10px !important;
            font-family: 'Helvetica Neue', Arial, sans-serif !important;
            font-size: 1.1em !important;
            line-height: 1.6 !important;
            color: #333 !important;
        }

        /* 
           Top-level h2 styling, e.g. .tutor-title
        */
        h2 {
            margin-bottom: 10;
            padding-bottom: 0px;
        }

        /* ---------------- LANDING PAGE STYLES ---------------- */
        .welcome-title {
            font-size: 36px;
            color: #333333;
            margin-bottom: 10px;
            text-align: center;
        }
        .welcome-subtitle {
            font-size: 18px;
            color: #666666;
            margin-bottom: 20px;
            text-align: center;
        }
        .section-button {
            background-color: #ffffff;
            border: 2px solid #007bff;
            color: #007bff;
            padding: 15px;
            font-size: 18px;
            border-radius: 8px;
            transition: background-color 0.3s, color 0.3s, border-color 0.3s;
            cursor: pointer;
            box-shadow: 0 2px 5px rgba(0, 123, 255, 0.1);
            text-align: center;
        }
        .section-button:hover {
            background-color: #007bff;
            color: #ffffff;
            border-color: #0056b3;
        }
        .section-buttons-container {
            width: 100%;
            max-width: 600px;
        }

        /* ---------------- Adjust Dropdown Menu ---------------- */
        /* Ensure the dropdown menu appears correctly */
        .navbar .dropdown-menu {
            right: 40;
            left: 0;
            align: right;
        }

        /* Optional: Style for feedback messages */
        .feedback-text {
            margin-top: 10px;
            font-size: 16px;
            color: #333;
            text-align: center;
        }
        """
    ),
)

def get_question_seed(section, question, subq):
    """Generate a consistent seed for a given question and sub-question"""
    return hash(f"{section}_{question}_{subq}") & 0xFFFFFFFF

def server(input, output, session):
    # Reactive values
    current_order = reactive.Value([])
    current_section = reactive.Value("")
    current_question = reactive.Value("")
    current_subq = reactive.Value(0)
    show_solution = reactive.Value(False)
    feedback_text = reactive.Value("")
    current_answer = reactive.Value(None)
    current_units = reactive.Value("Select units")

    def reset_state():
        current_subq.set(0)
        show_solution.set(False)
        feedback_text.set("")
        current_answer.set(None)
        current_units.set("Select units")

    # **Helper Function to Create Observers for Landing Page Section Buttons**
    def create_section_observer(button_id, section):
        @reactive.Effect
        @reactive.event(input[button_id])
        def _(_section=section):
            # Action buttons increment their value on click
            if input[button_id]() > 0:
                current_section.set(_section)
                is_section_selected.set(True)
                reset_state()
                # Show a notification
                show_new_notification(f"Section '{_section}' selected. Let's begin!", duration=3, notif_type="message")

    # **Create Observers for All Landing Page Section Buttons**
    for section in sections:
        button_id = f"section_button_{sanitize_id(section)}"
        create_section_observer(button_id, section)

    # **Conditional UI Rendering (Modified)**
    @output
    @render.ui
    def main_ui():
        if not is_section_selected():
            return landing_page_ui
        else:
            return ui.div(
                ui.row(
                    ui.column(
                        12,
                        ui.navset_bar(
                            # **Added Hamburger Menu Labeled "Choose Topic"**
                            ui.nav_menu(
                                "Choose Topic",
                                *[ui.nav_panel(section, value=section) for section in sections],
                            ),
                            id="section_nav",
                            title=ui.div(
                                ui.h2("Biomechanics Tutor", class_="tutor-title"),
                                class_="title-container"
                            ),
                            bg="#f8f9fa",
                            selected=current_section(),  # Dynamically set selected tab
                        ),
                    )
                ),
                # **Add Section Indicator for Debugging**
                ui.output_ui("question_nav"),
                ui.output_ui("question_card"),
                ui.output_ui("main_content"),
            )

    # **Existing Section Navigation Logic**
    @reactive.Effect
    @reactive.event(input.section_nav)
    async def _():
        selected = input.section_nav()
        if selected in sections:
            current_section.set(selected)
            current_question.set("")
            reset_state()

            section_questions = df[df["section"] == selected]
            unique_questions = section_questions.drop_duplicates("question_number")
            if not unique_questions.empty:
                current_question.set(unique_questions.iloc[0]["main_question"])

        # Only collapse if not the first load (navbar toggle)
        if not initial_load():
            await session.send_custom_message("collapse-navbar", {})
        else:
            initial_load.set(False)

    # **Section Indicator Output**
    @output
    @render.text
    def current_section_indicator():
        if not current_section():
            return "Please select a section from the menu"
        return f"Current Section: {current_section()}"

    @output
    @render.ui
    def question_nav():
        if not current_section():
            return None

        section_questions = df[df["section"] == current_section()]
        unique_questions = section_questions.drop_duplicates("question_number")

        nav_items = []
        for _, row in unique_questions.iterrows():
            nav_items.append(
                ui.nav_panel(f"{row['question_number']}", value=row["main_question"])
            )

        return ui.div(
            ui.navset_tab(*nav_items, id="question", selected=current_question()),
            class_="question_tabs"
        )

    @reactive.Effect
    @reactive.event(input.question)
    def _():
        if input.question():
            current_question.set(input.question())
            reset_state()

    @output
    @render.ui
    async def question_card():
        if not current_section() or not current_question():
            return None

        q_data = df[
            (df["section"] == current_section())
            & (df["main_question"] == current_question())
        ]
        if q_data.empty:
            return None

        main_row = q_data.iloc[0]

        top_content = [
            ui.div(
                ui.h3(
                    f"{current_section()} {main_row['question_number']}",
                    class_="question-title"
                ),
                class_="question-banner"
            ),
            ui.div(
                "",
                class_="markdown-base main-question-content",
                id="full-question",
                **{"data-markdown": main_row["full_question"]}
            ),
        ]

        # Use the CSV path as-is (absolute or relative)
        if pd.notna(main_row["image_url"]):
            top_content.append(
                ui.tags.img(
                    src=main_row["image_url"],
                    style="max-width: 100%; height: auto; margin: 10px -15px;",
                )
            )

        if show_solution() and pd.notna(main_row["solution"]):
            top_content.append(
                ui.div(
                    ui.h3("Solution", class_="question-title"),
                    ui.tags.div(
                        "",
                        class_="solution-markdown-content",
                        id="solution-content",
                        **{"data-markdown": main_row["solution"]}
                    ),
                    style="margin-top: 15px;"
                )
            )
            await session.send_custom_message('render-math', {'selector': '#solution-content'})

        units_options = [
            "Select units", "m/s", "m/s^2", "rad/s","rad/s^2", "N",
            "N/m", "kg", "m", "J", "W", "No units", "s", "Degrees","Revolutions","RPM", "N.m","kg.m^2", "kg.m/s"
        ]
        value = current_answer() if current_answer() is not None else 0

        bottom_content = ui.div(
            ui.row(
                ui.column(
                    4,
                    ui.input_numeric("numeric_answer", "", value=value),
                    style="max-width: 100%; height: auto; margin: 0px -20px;",
                ),
                ui.column(
                    3,
                    ui.input_select("units_answer", "", units_options, selected=current_units()),
                ),
                ui.column(
                    5,
                    ui.output_text("combined_answer"),
                ),
            ),
            ui.input_action_button("submit_answer", "Submit Answer", class_="btn-primary"),
            class_="answer-content"
        )

        # Minimal functional change: ensure DOM exists on first load before rendering markdown
        if initial_load():
            await asyncio.sleep(0.15)
            initial_load.set(False)
        await session.send_custom_message('render-math', {'selector': '#full-question'})

        return ui.card(
            ui.div(*top_content, style="padding-top: 10px;"), 
            ui.div(bottom_content, style="padding-bottom: 10px;"), 
            style="margin-bottom: 10px;"
        )

    @output
    @render.ui
    async def main_content():
        if not current_section() or not current_question():
            return None

        q_data = df[
            (df["section"] == current_section())
            & (df["main_question"] == current_question())
        ]
        sub_questions = list(q_data["sub_question"].unique())

        nav_panels = []
        for i, sq in enumerate(sub_questions):
            sq_data = q_data[q_data["sub_question"] == sq]
            subq_id = f"subq-{i}"

            if i == current_subq():
                options = []
                for j in range(4):
                    option_text = sq_data.iloc[0][f"option_{j+1}"]
                    # Minimal functional fix: skip NaN/blank/none options so last step shows no cards
                    if pd.isna(option_text) or str(option_text).strip().lower() in ("", "nan", "none"):
                        continue

                    if str(option_text).startswith(("http://", "https://")):
                        button_content = ui.tags.img(
                            src=option_text,
                            style="max-width: 100%; height: auto;",
                        )
                    else:
                        button_content = ui.div(
                            "",
                            class_="markdown-content",
                            id=f"opt_{i}_{j}-content",
                            **{"data-markdown": option_text}
                        )
                    options.append(
                        {
                            "content": button_content,
                            "option_text": option_text,
                            "feedback": sq_data.iloc[0][f"feedback_{j+1}"],
                            "index": j,
                            "original_index": j + 1,
                            "is_correct": sq_data.iloc[0]["correct_option"] == (j + 1),
                        }
                    )
                random.shuffle(options)
                current_order.set(options)

                subq_content = [
                    ui.div(
                        "",
                        class_="markdown-content",
                        id=subq_id,
                        **{"data-markdown": sq}
                    ),
                ]
                if options:
                    subq_content.append(
                        ui.layout_columns(*[
                            ui.card(
                                ui.input_action_button(
                                    f"opt_{i}_{idx}",
                                    opt["content"],
                                    class_="btn-block option-button",
                                ),
                                class_="option-button-card",
                                height="100%",
                            )
                            for idx, opt in enumerate(options)
                        ])
                    )

                content = [
                    ui.card(
                        ui.div(
                            ui.h3("Solution Steps", class_="question-title2"),
                            class_="question-banner2"
                        ),
                        *subq_content
                    )
                ]
            else:
                content = [
                    ui.card(
                        ui.div(
                            ui.h3("Solution Steps", class_="question-title2"),
                            class_="question-banner2"
                        ),
                        ui.div(
                            "",
                            class_="markdown-content",
                            id=subq_id,
                            **{"data-markdown": sq}
                        )
                    )
                ]

            nav_panels.append(
                ui.nav_panel(f"Step {i+1}", *content)
            )

        await session.send_custom_message('render-math', {'selector': '.markdown-content'})

        return ui.div(
            ui.navset_pill(
                *nav_panels,
                id="question_steps",
                selected=f"Step {current_subq() + 1}",
            ),
            class_="question_steps"
        )

    @output
    @render.text
    def combined_answer():
        if input.numeric_answer() is not None and input.units_answer() != "Select units":
            return f"{input.numeric_answer()} {input.units_answer()}"
        elif input.numeric_answer() is not None:
            return f"{input.numeric_answer()} (no units selected)"
        return ""

    def show_new_notification(msg, *, duration=5, notif_type="message"):
        old_id = last_notification_id()
        if old_id is not None:
            ui.notification_remove(old_id)
            last_notification_id.set(None)

        new_id = ui.notification_show(
            ui.HTML(msg),
            duration=duration,
            type=notif_type
        )
        last_notification_id.set(new_id)

    def create_option_observer(sub_q, opt):
        @reactive.Effect
        @reactive.event(input[f"opt_{sub_q}_{opt}"])
        async def _():
            q_data = df[
                (df["section"] == current_section())
                & (df["main_question"] == current_question())
            ]
            sub_questions = list(q_data["sub_question"].unique())
            if sub_q >= len(sub_questions):
                return  # Prevent index out of range
            sub_q_data = q_data[q_data["sub_question"] == sub_questions[sub_q]]
            options = current_order()
            if opt >= len(options):
                return  # Prevent index out of range
            clicked_option = options[opt]
            feedback_message = sub_q_data.iloc[0][
                f"feedback_{clicked_option['original_index']}"
            ]
            is_correct = (
                clicked_option["original_index"]
                == sub_q_data.iloc[0]["correct_option"]
            )

            if is_correct and current_subq() < len(sub_questions) - 1:
                current_subq.set(current_subq() + 1)
                await session.send_custom_message(
                    'render-math', {'selector': f'#subq-{current_subq()}'}
                )
                show_new_notification("Correct! Moving to next step.", duration=3, notif_type="message")
            elif is_correct:
                show_new_notification("Correct! Please enter your final answer.", duration=3, notif_type="message")
            else:
                show_new_notification(feedback_message, duration=5, notif_type="warning")
                await session.send_custom_message(
                    'render-math', {'selector': '#feedback_message'}
                )

    # **Create Observers for All Option Buttons**
    for i in range(10):
        for j in range(4):
            create_option_observer(i, j)

    # **Answer Submission Observer**
    @reactive.Effect
    @reactive.event(input.submit_answer)
    async def check_numeric():
        if input.numeric_answer() is None:
            feedback_text.set("")
            return

        current_answer.set(input.numeric_answer())
        current_units.set(input.units_answer())

        q_data = df[
            (df["section"] == current_section())
            & (df["main_question"] == current_question())
        ]
        if q_data.empty:
            return

        correct_range = [
            float(q_data.iloc[0]["min_value"]),
            float(q_data.iloc[0]["max_value"])
        ]
        selected_units = input.units_answer()
        correct_units = q_data.iloc[0]["units"]

        numeric_correct = correct_range[0] <= input.numeric_answer() <= correct_range[1]
        units_correct = selected_units == correct_units

        if numeric_correct and units_correct:
            show_solution.set(True)
            feedback_text.set("Correct! View the complete solution below.")
            show_new_notification(
                "Correct! You can now view the complete solution.",
                duration=5,
                notif_type="message",
            )
            await session.send_custom_message('render-math', {'selector': '#solution-content'})
        elif numeric_correct and not units_correct:
            show_solution.set(False)
            if selected_units == "Select units":
                msg = "Your numeric answer is correct! Please select the appropriate units."
            else:
                msg = "Your numeric answer is correct, but the units are incorrect. Try again!"
            feedback_text.set(msg)
            show_new_notification(msg, duration=5, notif_type="warning")
        else:
            show_solution.set(False)
            feedback_text.set("Try again. Your answer is not within the acceptable range.")
            show_new_notification(
                "Try again. Your answer is not within the acceptable range.",
                duration=5,
                notif_type="warning",
            )

    # **Feedback Display Output**
    @output
    @render.text
    def feedback_display():
        return feedback_text()

# point Shiny at your www/ folder so anything under www/ is served at /
www_path = Path(__file__).parent / "www"
app = App(app_ui, server, static_assets=www_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
