# -*- coding: utf-8 -*-

from odoo import fields, models, tools, api
from odoo.tools.translate import _
import tempfile
import csv
import base64
from odoo.exceptions import UserError

class MonthlyBankReportWizard(models.TransientModel):
    _name = 'monthly.bank.report.wizard'
    _description = 'Bank Report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    def generate_bank_report(self):
        # Fetch payslip records between the selected start_date and end_date
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
        ])

        # Generate the CSV report
        return self._generate_csv_report(payslips)

    def _generate_csv_report(self, payslips):

        context = self.env.context
        if context is None:
            context = {}
        context = dict(context)



        csv_tmp_filename = tempfile.mktemp('.' + "csv")

        report_column_headers = ['Employee Number', 'Bank Code', 'Employee Name', 'Bank Account Number', 'Net Pay']

        try:
            report_csv_file = open(csv_tmp_filename, 'w')
        except IOError:
            raise UserError(_('Can not open the file : %s') % (csv_tmp_filename))

        writer = csv.writer(report_csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(report_column_headers)

        for payslip in payslips:
            report_values = []
            employee = payslip.employee_id
            bank_account = employee.bank_account_id
            report_values.append(employee.identification_id or '')
            report_values.append(bank_account.bank_id.bic or '')
            report_values.append(employee.name or '')
            report_values.append(bank_account.acc_number or '')
            report_values.append(payslip.net_wage or 0 or '')
            writer.writerow(report_values)

        report_csv_file.close()

        # Generate file name:
        download_file_name = 'Monthly_Bank_Report_export.csv'

        # Attach CSV file from temp path to odoo to give download ability to user
        file = open(csv_tmp_filename, "rb")
        out = file.read()
        file.close()
        res = base64.b64encode(out)
        module_rec = self.env['download.monthly.bank.report'].create({
            'name': download_file_name,
            'exported_csv_file': res
        })

        return {
            'name': _('Download Report'),
            'res_id': module_rec.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'download.monthly.bank.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }


class BinaryExportedReportWizard(models.TransientModel):
    _name = 'download.monthly.bank.report'

    name = fields.Char(string='Name', size=64, default='Monthly_Bank_Report.csv')
    exported_csv_file = fields.Binary('Click On Link To Download File', readonly=True)