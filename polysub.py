""" Transcribe & Translate - PolySub App Layout using Flet """

import flet as ft
from flet import (
    UserControl,
    Page,
    Column,
    Row,
    Container,
    Text,
    padding,
    alignment,
    IconButton,
    Image,
    FilledTonalButton,
    Dropdown,
    ProgressBar,
    FilledButton,
)

# Main Class
class PolySub(UserControl):
    # test colors
    color1 = ft.colors.RED
    color2 = ft.colors.GREEN
    color3 = ft.colors.BLUE

    # Navigation Container
    def NavContainer(self):
        self.nav = Container(
            Row(
                controls=[
                    Container(
                        Image(src='images/logo@8x.png', width=300),
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=2,
                    ),
                    Container(
                        Row(
                            controls=[
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    IconButton(icon='question_mark_rounded', aspect_ratio=1, scale=1),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    IconButton(icon='settings', aspect_ratio=1, scale=1),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.nav

    # Main Container
    def MainContainer(self):
        self.main = Container(
            Row(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    FilledTonalButton(
                                        "Select Videos", 
                                        icon="file_upload_outlined",
                                        on_click=lambda x: print("Hello World"),
                                        expand=1,
                                        width=450, # ! Temp solution
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    Text(
                                        'You can drag & drop your videos!',
                                        size=17,
                                        color=ft.colors.BLACK12,
                                        weight=ft.FontWeight.W_100,
                                        text_align=ft.TextAlign.CENTER,
                                        width=450, # ! Temp solution
                                    ),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    Dropdown(
                                        options=[
                                            ft.dropdown.Option("Red"),
                                        ],
                                        hint_text="Select Input Language",
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    Dropdown(
                                        options=[
                                            ft.dropdown.Option("Red"),
                                        ],
                                        hint_text="Select Output Language",
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    Text(
                                        'This Step is optional',
                                        size=17,
                                        color=ft.colors.BLACK12,
                                        weight=ft.FontWeight.W_100,
                                        text_align=ft.TextAlign.CENTER,
                                        width=450, # ! Temp solution
                                    ),
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    FilledTonalButton(
                                        "Select Save Path", 
                                        icon="folder_open",
                                        on_click=lambda x: print("Hello World"),
                                        expand=1,
                                        width=450, # ! Temp solution
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        self.LogContainer(),
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=3,
        )

        return self.main

    # Function Container
    def SubmitContainer(self):
        self.submit = Container(
            Row(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    ProgressBar(
                                        width=900, # ! Temp solution
                                        bar_height=4,
                                        value=0.01,
                                        color="amber", 
                                        bgcolor="#eeeeee",
                                    ), 
                                    expand=1,
                                    padding=padding.all(20),
                                ),
                                Container(
                                    FilledButton(
                                        "Start Transcribing",
                                        on_click=lambda x: print("Hello World"),
                                        expand=1,
                                        width=900, # ! Temp solution
                                        style=ft.ButtonStyle(
                                            shape=ft.RoundedRectangleBorder(radius=10),
                                        ),
                                    ),
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        padding=padding.all(0),
                        expand=6,
                    ),
                    Container(
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.submit

    # Footer Container
    def FooterContainer(self):
        self.footer = Container(
            Column(
                controls=[
                    Container(
                        padding=padding.all(0),
                        expand=2,
                    ),
                    Container(
                        Text(
                            'All Rights Reserved © 2023',
                            size=17,
                            color=ft.colors.BLACK12,
                            weight=ft.FontWeight.W_100,
                            text_align=ft.TextAlign.CENTER,
                            width=1200, # ! Temp solution  
                        ),
                        padding=padding.all(0),
                        expand=1,
                    )
                ],
            ),
            padding=0,
            expand=1,
        )

        return self.footer

    # Log Container
    def LogContainer(self):
        self.log_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=padding.all(20),
                auto_scroll=True,
            )
        self.log_containter = Container(
            self.log_view,
            width=450, # ! Temp solution
            height=500, # ! Temp solution
            bgcolor='#333536',
        )
        return self.log_containter

    def build(self):
        return Column(
            controls=[
                self.NavContainer(),
                self.MainContainer(),
                self.SubmitContainer(),
                self.FooterContainer(),
            ],
            width=1200,
            height=1050,
        )

def start(page: Page):
    page.title = "PolySub - Transcribe & Translate"

    page.horizontal_alignment = 'center'
    page.vertical_alignment = 'center'

    page.theme = ft.Theme(color_scheme_seed=ft.colors.INDIGO)

    page.window_height = 1100
    page.window_width = 1200
    page.window_resizable = False
    page.padding = padding.all(0)

    # page.window_min_height = 600
    # page.window_min_width = 900

    # page.window_max_height = 800
    # page.window_max_width = 1200

    app = PolySub(page)
    page.add(app)
    page.update()

if __name__ == '__main__':
    ft.app(target=start)
