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
    alignment
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
                        bgcolor=ft.colors.RED_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        bgcolor=ft.colors.RED_200,
                        padding=padding.all(0),
                        expand=2,
                    ),
                    Container(
                        Row(
                            controls=[
                                Container(
                                    bgcolor=ft.colors.RED_700,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.RED_700,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.RED_700,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                            ],
                        ),
                        bgcolor=ft.colors.RED_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            bgcolor=self.color1,
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
                        bgcolor=ft.colors.GREEN_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_800,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_800,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        bgcolor=ft.colors.GREEN_200,
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        bgcolor=ft.colors.GREEN_200,
                        padding=padding.all(0),
                        expand=3,
                    ),
                    Container(
                        bgcolor=ft.colors.GREEN_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            bgcolor=self.color2,
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
                        bgcolor=ft.colors.BLUE_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                    Container(
                        Column(
                            controls=[
                                Container(
                                    bgcolor=ft.colors.BLUE_600,
                                    padding=padding.all(0),
                                    expand=1,
                                ),
                                Container(
                                    bgcolor=ft.colors.BLUE_600,
                                    padding=padding.all(0),
                                    expand=2,
                                ),
                            ],
                        ),
                        bgcolor=ft.colors.BLUE_200,
                        padding=padding.all(0),
                        expand=6,
                    ),
                    Container(
                        bgcolor=ft.colors.BLUE_200,
                        padding=padding.all(0),
                        expand=1,
                    ),
                ],
            ),
            bgcolor=self.color3,
            padding=0,
            expand=1,
        )

        return self.submit

    # Footer Container
    def FooterContainer(self):
        self.footer = Container(
            
            bgcolor=self.color2,
            padding=0,
            expand=1,
        )

        return self.footer

    def build(self):
        return Column(
            controls=[
                self.NavContainer(),
                self.MainContainer(),
                self.SubmitContainer(),
                self.FooterContainer(),
            ],
            width=1200,
            height=1000,
        )

def start(page: Page):
    page.title = "PolySub - Transcribe & Translate"

    page.horizontal_alignment = 'center'
    page.vertical_alignment = 'center'

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
