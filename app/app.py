import reflex as rx
from app.state import State


def index() -> rx.Component:
    """The main view of the app."""
    return rx.el.main(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("waves", class_name="mx-auto h-12 w-12 text-gray-400"),
                    rx.el.h1(
                        "Hello World",
                        class_name="mt-6 text-center text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-600 sm:text-6xl",
                    ),
                    rx.el.p(
                        "A beautifully simple starting point for your next Reflex project.",
                        class_name="mt-4 max-w-md text-center text-lg font-medium text-gray-500",
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Get Started",
                            rx.icon("arrow-right", class_name="ml-2 h-4 w-4"),
                            on_click=lambda: rx.redirect(
                                "https://reflex.dev/docs/getting-started/introduction"
                            ),
                            class_name="mt-8 inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-semibold rounded-xl text-white bg-orange-500 hover:bg-orange-600 transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-orange-500/50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500",
                        ),
                        class_name="mt-10 flex justify-center",
                    ),
                ),
                class_name="p-8 sm:p-12 md:p-16 bg-white rounded-2xl shadow-lg border border-gray-200/50 transform transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl",
            ),
            class_name="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-4 font-['JetBrains_Mono']",
        ),
        class_name="font-['JetBrains_Mono'] bg-gray-50",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index)