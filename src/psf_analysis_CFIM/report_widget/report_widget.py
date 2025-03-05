import os

from reportlab.lib import colors
from qtpy.QtWidgets import QGroupBox, QFormLayout, QWidget, QHBoxLayout, QFileDialog, QLineEdit, QPushButton, QLabel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


class WarningMessage:
    def __init__(self, message:str, is_ignored:bool=False):
        self.message = message
        self.is_ignored = is_ignored

class WarningMessageList:
    def __init__(self, list_of_warnings: list[WarningMessage]=[]):
        self.warnings = list_of_warnings

    def add_warning(self, warning):
        self.warnings.append(warning)

class ErrorMessageList(WarningMessageList):
    def __init__(self, list_of_warnings: list[WarningMessage]=[]):
        super().__init__(list_of_warnings)

    def add_error(self, error):
        self.warnings.append(error)


def _get_unique_filepath(path):
    """
        If the filepath already exists, appends a counter to the base name.
        E.g., if 'example_report.pdf' exists, it returns 'example_report(1).pdf'.
        """
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1
    new_filepath = f"{base}({counter}){ext}"
    while os.path.exists(new_filepath):
        counter += 1
        new_filepath = f"{base}({counter}){ext}"
    return new_filepath





class ReportWidget(QWidget):
    def __init__(self,parent=None, filename = "Report", title = "Report", output_path=None):
        super().__init__(parent)
        self.border_color = colors.green
        self.bead_variation = None
        self.filename = filename
        self.title = title
        self.bead_data_to_show: list[dict] = []
        self._canvas = None
        self._path = None
        self._output_path = output_path
        self._bead_keys = ["z_fwhm", "y_fwhm", "x_fwhm"]
        self.save_dir_line_edit = None
        self.save_path = None

        # Don't ask why I made these into their own types, I just did.
        self.warnings = WarningMessageList()
        self.errors = ErrorMessageList()

    def set_title(self, title):
        self.title = title

    def add_bead_stats(self, stats, title="Average bead"):
        """
            Add bead stats to the report.
        """
        bead_stats = {"title": title}
        for key in self._bead_keys:
            bead_stats[key] = int(stats[key])
        self.bead_data_to_show.append(bead_stats)

    def add_bead_stats_psf(self, stats, title="Average bead"):
        """
            Reformats a PSFRecord and calls add_bead_stats.
        """
        bead_stats = {
            "z_fwhm": stats.z_fit.z_fwhm,
            "y_fwhm": stats.yx_fit.y_fwhm,
            "x_fwhm": stats.yx_fit.x_fwhm,
        }
        self.add_bead_stats(bead_stats, title)
    def set_averaged_bead(self, bead):
        """
            Set the averaged bead.
        """
        self.bead_variation = bead

    def set_bead_variation(self, stats):
        """
            Set the bead variation.
        """
        variation_bead = {
            "title": "Bead Variation",
            "z_fwhm": f"{int(stats["z_fwhm_max"])} - {int(stats["z_fwhm_min"])}",
            "y_fwhm": f"{int(stats["y_fwhm_max"])} - {int(stats["y_fwhm_min"])}",
            "x_fwhm": f"{int(stats["x_fwhm_max"])} - {int(stats["x_fwhm_min"])}",
        }
        self.bead_variation = variation_bead

    def add_warnings_and_errors(self, warnings:WarningMessageList, errors:ErrorMessageList):
        """
            Add warnings and errors to the report.
        """
        self.warnings.add_warning(warnings)
        self.errors.add_error(errors)

    def create_pdf(self, path=None):

        self._path = path

        if not os.path.exists(self._path):
            raise FileNotFoundError(f"Directory {self._path} does not exist.")

        path_filename = os.path.join(self._path, self.filename + ".pdf")

        filepath = _get_unique_filepath(path_filename)
        #
        # c = canvas.Canvas(filename=unique_filepath, pagesize=letter, lang="en-gb")
        # c.setTitle(self.title)
        #
        # width, height = letter
        #
        # # Set title font and size
        # c.setFont("Helvetica-Bold", 24)
        # # Draw the title centered on the page
        # c.drawCentredString(width / 2.0, height - 100, self.title)
        #
        # # Additional content like stats, warnings, errors, and grade can be added here.
        # # For example, to add some text:
        # c.setFont("Helvetica", 12)
        # c.drawString(100, height - 150, "Overall stats, warnings, and grade will appear here.")
        #
        # c.showPage()
        # self._canvas = c
        # Create a PDF document using Platypus


        doc = SimpleDocTemplate(filepath, pagesize=letter)
        doc.title = self.title
        styles = getSampleStyleSheet()
        story = []

        # Add the title
        story.append(Paragraph(self.title, styles["Title"]))
        story.append(Spacer(1, 12))

        # Add the bead variation if it exists
        if self.bead_variation:
            data = self.bead_data_to_show + [self.bead_variation]
        else:
            data = self.bead_data_to_show

        # Create table data with header and measurement rows.
        table_data = self.beads_to_schema(data, styles["BodyText"])

        # Create the table and set a style for it
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(table)
        doc.build(
            story,
            onFirstPage=lambda canvas, doc: self.draw_border(canvas, doc),
            onLaterPages=lambda canvas, doc: self.draw_border(canvas, doc)
        )
        print(f"Report saved as: {filepath}")

    def draw_border(self,canvas, doc):
        """
            Draws a border on the current canvas with the specified border_color.
            """
        canvas.saveState()
        canvas.setStrokeColor(self.border_color)
        canvas.setLineWidth(4)  # Adjust the thickness as needed
        margin = 0.5 * inch  # Set margin from the page edge
        width, height = doc.pagesize
        canvas.rect(margin, margin, width - 2 * margin, height - 2 * margin)
        canvas.restoreState()

    def init_ui(self):
        pane = QGroupBox(parent=self)
        pane.setLayout(QFormLayout())

        dir_selection_dialog = QWidget(parent=self)
        dir_selection_dialog.setLayout(QHBoxLayout())

        self.save_path = QFileDialog()
        self.save_path.setFileMode(QFileDialog.DirectoryOnly)
        self.save_path.setDirectory(
            str(self._output_path)
        )

        self.save_dir_line_edit = QLineEdit()
        self.save_dir_line_edit.setText(self.save_path.directory().path())

        choose_dir = QPushButton("...")
        choose_dir.clicked.connect(self.parent().select_save_dir)

        dir_selection_dialog.layout().addWidget(
            QLabel("Save Dir", dir_selection_dialog)
        )
        dir_selection_dialog.layout().addWidget(self.save_dir_line_edit)
        dir_selection_dialog.layout().addWidget(choose_dir)

        pane.layout().addRow(dir_selection_dialog)

        self.save_button = QPushButton("Save Measurements")
        self.save_button.setEnabled(True)
        self.save_button.clicked.connect(self.parent().save_measurements)

        pane.layout().addRow(self.save_button)

        return pane

    def beads_to_schema(self, beads, style):
        """
        Convert a list of bead measurement dictionaries to a table schema.

        """
        # Define header
        headers = [Paragraph(item, style) for item in ["Bead"] + self._bead_keys]
        schema = [headers]

        # Append each bead's measurements in order
        for bead in beads:
            row = [
                Paragraph(str(bead.get("title", "N/A")), style),
                Paragraph(str(bead.get("z_fwhm", "N/A")), style),
                Paragraph(str(bead.get("y_fwhm", "N/A")), style),
                Paragraph(str(bead.get("x_fwhm", "N/A")), style)
            ]
            schema.append(row)
        return schema

# if __name__ == "__main__":
#     path_string = "C:/napari-psf-analysis-CFIM-edition/src/psf_analysis_CFIM/report_widget/dev_output"
#     report = ReportWidget(filename="example_report.pdf", "PSF Analysis Report")
#     report.create_pdf(path=path_string)
#     report.save_pdf(path_string)