from odoo import fields, models
import xlsxwriter
from io import BytesIO
import base64

class P10ReportWizard(models.TransientModel):
    _name = 'p10.m.report.wizard'
    _description = 'P10-M-Report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    def generate_p10_m_report(self):
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
            ('state', '=', 'done'),
        ])

        return self._m_generate_excel_report(payslips)

    def _m_generate_excel_report(self, payslips):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        title_format = workbook.add_format({
            'bold': True, 'bg_color': '#FF0000', 'font_size': 11, 'align': 'center',
            'valign': 'vcenter', 'font_color': 'white'
        })

        normal_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True  # Enable text wrapping
        })

        total_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True , 'bg_color': 'black','font_color': 'white'
        })

        # Affordable Housing Levy Details Sheet
        housing_levy_details_worksheet = workbook.add_worksheet('M_Affordable Housing Levy_Dtls')

        # Set column widths for the new sheet
        housing_levy_details_worksheet.set_column(0, 7, 25)  # Set width for all columns

        # Set row heights for the new sheet
        housing_levy_details_worksheet.set_row(0, 30)  # Height for the title row
        housing_levy_details_worksheet.set_row(1, 30)  # Height for the header row

        # Add title
        housing_levy_details_worksheet.merge_range('A1:H1', 'Section M: Details of Affordable Housing Levy', title_format)

        # Define the headers for the new sheet
        levy_headers = [
            "Member Number (ID Number)", "Member Name", "KRA PIN", "Gross Salary",
            "Basic Salary", "Member Contribution - Housing Levy (A)", "Employer Contribution (B)",
            "Total Contribution (A + B) (KShs)"
        ]
        housing_levy_details_worksheet.write_row('A2', levy_headers)

        row = 3  # Start data from row 4
        for payslip in payslips:
            employee = payslip.employee_id
            contract = payslip.contract_id

            # Employee data to be added in each row
            employee_data = [
                employee.identification_id,
                employee.name,
                employee.l10n_ke_kra_pin,
                contract.wage,

            ]
            housing_levy_details_worksheet.write_row(row, 0, employee_data, normal_format)
            row += 1
        row += 2
        # Add sum of total contributions at the end
        housing_levy_details_worksheet.merge_range(f'F{row}:G{row}', 'Sum of Total Contribution', total_format)
        housing_levy_details_worksheet.write_formula(f'H{row}', f'SUM(H3:H{row-1})', normal_format)

        # Close workbook and return file
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        download_file_name = f'Affordable Housing Levy{self.start_date}_{self.end_date}.xlsx'

        # Create the record to allow file download
        module_rec = self.env['download.m.p10.report'].create({
            'name': download_file_name,
            'exported_excel_file': file_data
        })

        return {
            'name': 'Download P10 M Report',
            'res_id': module_rec.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'download.m.p10.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class DownloadP10Report(models.TransientModel):
    _name = 'download.m.p10.report'
    _description = 'Download P10M Report'

    name = fields.Char(string='File Name', size=64, default='P10_M_Report.xlsx')
    exported_excel_file = fields.Binary('Click to Download File', readonly=True)
