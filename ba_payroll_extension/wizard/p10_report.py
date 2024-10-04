from odoo import fields, models
import xlsxwriter
from io import BytesIO
import base64

class P10ReportWizard(models.TransientModel):
    _name = 'p10.report.wizard'
    _description = 'P10 Report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    def generate_p10_report(self):
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
            ('state', '=', 'done'),
        ])

        return self._generate_excel_report(payslips)

    def _generate_excel_report(self, payslips):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('B_Employees_Dtls')

        # Define formatting
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#595959', 'color': 'white', 'align': 'center',
            'valign': 'vcenter', 'border': 1, 'text_wrap': True  # Enable text wrapping
        })

        sub_header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True  # Enable text wrapping
        })

        title_format = workbook.add_format({
            'bold': True, 'bg_color': '#FF0000', 'font_size': 11, 'align': 'center',
            'valign': 'vcenter', 'font_color': 'white'
        })

        normal_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True  # Enable text wrapping
        })

        total_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'bg_color': 'black',
            'font_color': 'white'
        })

        # Set column widths (increase values as needed)
        worksheet.set_column(0, 33, 25)  # Set width for all columns

        # Adjust row heights for better visibility of wrapped text
        worksheet.set_row(0, 20)  # Height for the title row
        worksheet.set_row(1, 30)  # Height for the header row
        worksheet.set_row(2, 50)  # Height for the subheader row

        # Add title
        worksheet.merge_range('A1:AG1', 'Section B : Details of Salary Paid and PAYE deducted from Employee(s)',
                              title_format)

        # Main headers
        worksheet.merge_range('A2:D2', '', header_format)
        worksheet.merge_range('E2:M2', 'Cash Pay (Ksh)', header_format)
        worksheet.merge_range('N2:P2', 'Non Cash Benefits (Ksh)', header_format)
        worksheet.merge_range('R2:V2', 'Housing Benefit (Ksh)', header_format)
        worksheet.merge_range('X2:AC2', 'Benefits (Ksh)\nDefined / Pension Contribution Benefit (Ksh)', header_format)

        subheaders = [
            "PIN of Employee", "Name of Employee", "Residential Status", "Type of Employee",
        ]
        worksheet.write_row('A3', subheaders, sub_header_format)

        # Sub-headers for Cash Pay
        cash_pay_subheaders = [
            "Basic Salary", "Housing Allowance", "Transport Allowance", "Leave Pay",
            "Over Time Allowance", "Director's Fee", "Lump Sum Payment if any", "Other Allowance",
            "Total Cash Pay (A)"
        ]
        worksheet.write_row('E3', cash_pay_subheaders, sub_header_format)

        # Sub-headers for Non Cash Benefits
        non_cash_subheaders = [

            "Value of Car Benefit (Value of Car Benefit from D_Computation_of_ Car_Benefit)(B)",
            "Other Non Cash Benefits (C)", "Total Non Cash Pay (D)=(B + C) (C if greater than 3,000)",
            "Global Income (In case of non full time service Director) (Ksh) (E)"
        ]
        worksheet.write_row('N3', non_cash_subheaders, sub_header_format)

        # Sub-headers for Housing Benefits
        housing_subheaders = [
            "Type of Housing", "Rent of House/Market Value", "Computed Rent of House (F)",
            "Rent Recovered from Employee (G)",
            "Net Value of Housing (H) = (F - G)", "Total Gross Pay (I) = (A + D + E + H)"
        ]
        worksheet.write_row('R3', housing_subheaders, sub_header_format)

        # Sub-headers for Defined/Pension Contribution Benefit
        pension_subheaders = [
            "30% of Cash Pay (J) = (A * 30%)", "Actual Contribution (K)", "Permissible Limit (L)",
            "Mortgage Interest (Max 25000 Ksh a month) (M)",
            "Deposit on Home Ownership Saving Plan (Max 96,000 Ksh or 8,000 Ksh a month) (N)",
            "Amount of Benefit (O) = (Lower of J,K,L + M or N which ever is higher)",
            "Taxable Pay (P) = (I - O)", "Tax Payable (Q) = (P * Slab Rate)",
            "Monthly Personal Relief (Ksh) ( R )",
            "Amount of Insurance Relief (Total of Amount of Insurance Relief from E_Computation_of_Insu_Relief) (Ksh) (S)",
            "PAYE Tax (T) = (Q - R - S)", "Self Assessed PAYE Tax"
        ]
        worksheet.write_row('X3', pension_subheaders, sub_header_format)

        row = 3
        for payslip in payslips:
            employee = payslip.employee_id
            contract = payslip.contract_id
            salary_computation = payslip.line_ids
            house_allowance = transport_allowance = leave_allowance = overtime1_allowance = overtime2_allowance = directors_allowance = lump_allowance = other_allowance = car_allowance = 0

            for line in salary_computation:
                if line.name == 'House Allowances':
                    house_allowance = line.total
                if line.name == 'Transport Allowance':
                    transport_allowance = line.total
                if line.name == 'Overtime 1 (OT1)':
                    overtime1_allowance = line.total
                if line.name == 'Overtime 2 (OT2)':
                    overtime2_allowance = line.total
                if line.name == 'Directors Fee':
                    directors_allowance = line.total
                if line.name == 'Lump sum Payment':
                    lump_allowance = line.total
                if line.name == 'Other Allowances':
                    other_allowance = line.total
                if line.name == 'Car Benefit':
                    car_allowance = line.total
            overtime = overtime1_allowance + overtime2_allowance
            # Assuming fields exist or have been added to the employee model
            employee_data = [
                employee.l10n_ke_kra_pin,
                employee.name,
                employee.country_id.name,
                employee.employee_type,
                contract.wage,
                house_allowance,
                transport_allowance,
                leave_allowance,
                overtime,
                directors_allowance,
                lump_allowance,
                other_allowance,
                car_allowance,
            ]
            worksheet.write_row(row, 0, employee_data, normal_format)
            row += 1
        row += 2
        # Add sum of total contributions at the end
        worksheet.merge_range(f'AG{row}:AH{row}', 'Total', total_format)


        # Close workbook and return file
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        download_file_name = f'Employee Details{self.start_date}_{self.end_date}.xlsx'

        # Create the record to allow file download
        module_rec = self.env['download.p10.report'].create({
            'name': download_file_name,
            'exported_excel_file': file_data
        })

        return {
            'name': 'Download P10 Report',
            'res_id': module_rec.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'download.p10.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class DownloadP10Report(models.TransientModel):
    _name = 'download.p10.report'
    _description = 'Download P10 Report'

    name = fields.Char(string='File Name', size=64, default='P10_Report.xlsx')
    exported_excel_file = fields.Binary('Click to Download File', readonly=True)
