# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command
from datetime import timedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    overtime_hours_weekdays = fields.Float(string='Overtime Hours (Weekdays)', compute='_compute_overtime_hours')
    overtime_hours_sunday_holiday = fields.Float(string='Overtime Hours (Sunday/Public Holidays)',
                                                 compute='_compute_overtime_hours')

    overtime_amount_weekdays = fields.Float(string='Overtime Amount (Weekdays)', compute='_compute_overtime_amount')
    overtime_amount_sunday_holiday = fields.Float(string='Overtime Amount (Sunday/Public Holidays)',
                                                  compute='_compute_overtime_amount')




    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_overtime_hours(self):
        for payslip in self:
            overtime_weekdays = 0
            overtime_sunday_holiday = 0

            # Fetch actual attendance records for the employee
            attendance_records = self.env['hr.attendance'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('check_in', '>=', payslip.date_from),
                ('check_out', '<=', payslip.date_to)
            ])

            # Get the work schedule and public holidays
            public_holidays = self._get_public_holidays(payslip.date_from, payslip.date_to)

            for attendance in attendance_records:
                attendance_day = attendance.check_in.weekday()  # 0 = Monday, 6 = Sunday
                overtime_hours_data = attendance.overtime_hours
                time_string = self.convert_float_time_to_hours_minutes(overtime_hours_data)
                overtime_hours = self.convert_time_string_to_float(time_string)

                # Check if it's a Sunday or public holiday
                if attendance_day == 6 or attendance.check_in.date() in public_holidays:
                    # Overtime for Sundays and Public Holidays (OT2)
                    overtime_sunday_holiday += overtime_hours
                elif 0 <= attendance_day <= 4:  # Weekdays (Monday to Friday)
                    # Overtime for weekdays (OT1)
                    overtime_weekdays += overtime_hours

            payslip.overtime_hours_weekdays = overtime_weekdays
            payslip.overtime_hours_sunday_holiday = overtime_sunday_holiday

    def convert_float_time_to_hours_minutes(self, float_time):
        hours = int(float_time)
        minutes = round((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def convert_time_string_to_float(self, time_str):
        hours, minutes = map(int, time_str.split(':'))
        float_time = hours + (minutes / 60)
        return round(float_time, 2)


    @api.depends('overtime_hours_weekdays', 'overtime_hours_sunday_holiday')
    def _compute_overtime_amount(self):
        for payslip in self:
            basic_pay = payslip.contract_id.wage
            ot1_rate = 1.5
            ot2_rate = 2
            hourly_rate = basic_pay / 192

            payslip.overtime_amount_weekdays = payslip.overtime_hours_weekdays * hourly_rate * ot1_rate
            payslip.overtime_amount_sunday_holiday = payslip.overtime_hours_sunday_holiday * hourly_rate * ot2_rate

    def _get_public_holidays(self, date_from, date_to):
        # Fetch the list of public holidays between date_from and date_to
        holidays = self.env['resource.calendar.leaves'].search([
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('resource_id', '=', False)
        ])
        holiday_dates = set()
        for holiday in holidays:
            current_date = holiday.date_from.date()
            end_date = holiday.date_to.date()
            # Add all dates in the range from start date to end date
            while current_date <= end_date:
                holiday_dates.add(current_date)
                current_date += timedelta(days=1)
        return holiday_dates


    def action_print_payslip(self):
        # records = self.env['hr.payslip'].browse(self.ids)
        return self.env.ref('hr_payroll.action_report_payslip').report_action(self)

    def _get_payslip_lines(self):
        line_vals = []
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("There's no contract set on payslip %s for %s. Check that there is at least a contract set on the employee form.", payslip.name, payslip.employee_id.name))

            localdict = self.env.context.get('force_payslip_localdict', None)
            if localdict is None:
                localdict = payslip._get_localdict()

            rules_dict = localdict['rules']
            result_rules_dict = localdict['result_rules']

            blacklisted_rule_ids = self.env.context.get('prevent_payslip_computation_line_ids', [])

            result = {}
            for rule in sorted(payslip.struct_id.rule_ids, key=lambda x: x.sequence):
                if rule.id in blacklisted_rule_ids:
                    continue
                localdict.update({
                    'result': None,
                    'result_qty': 1.0,
                    'result_rate': 100,
                    'result_name': False
                })
                if rule._satisfy_condition(localdict):
                    # Retrieve the line name in the employee's lang
                    employee_lang = payslip.employee_id.lang
                    # This actually has an impact, don't remove this line
                    context = {'lang': employee_lang}
                    if rule.code in localdict['same_type_input_lines']:
                        for multi_line_rule in localdict['same_type_input_lines'][rule.code]:
                            localdict['inputs'].dict[rule.code] = multi_line_rule
                            amount, qty, rate = rule._compute_rule(localdict)
                            tot_rule = amount * qty * rate / 100.0
                            localdict = rule.category_id._sum_salary_rule_category(localdict,
                                                                                   tot_rule)
                            rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                            if rule_name == 'Overtime@1.5':
                                rule_name = 'Overtime@1.5' + '(' + (str(self.overtime_hours_weekdays)) + ')'
                            if rule_name == 'Overtime@2.0':
                                rule_name = 'Overtime@2.0' + '(' + (str(self.overtime_hours_sunday_holiday)) + ')'
                            if amount != 0:
                                line_vals.append({
                                    'sequence': rule.sequence,
                                    'code': rule.code,
                                    'name':  rule_name,
                                    'salary_rule_id': rule.id,
                                    'contract_id': localdict['contract'].id,
                                    'employee_id': localdict['employee'].id,
                                    'amount': amount,
                                    'quantity': qty,
                                    'rate': rate,
                                    'slip_id': payslip.id,
                                })
                    else:
                        amount, qty, rate = rule._compute_rule(localdict)
                        #check if there is already a rule computed with that code
                        previous_amount = localdict.get(rule.code, 0.0)
                        #set/overwrite the amount computed for this rule in the localdict
                        tot_rule = amount * qty * rate / 100.0
                        localdict[rule.code] = tot_rule
                        result_rules_dict[rule.code] = {'total': tot_rule, 'amount': amount, 'quantity': qty, 'rate': rate}
                        rules_dict[rule.code] = rule
                        # sum the amount for its salary category
                        localdict = rule.category_id._sum_salary_rule_category(localdict, tot_rule - previous_amount)
                        rule_name = payslip._get_rule_name(localdict, rule, employee_lang)
                        if rule_name == 'Overtime@1.5':
                            rule_name = 'Overtime@1.5' + '(' +(str(self.overtime_hours_weekdays))+ ')'
                        if rule_name == 'Overtime@2.0':
                            rule_name = 'Overtime@2.0' + '(' + (str(self.overtime_hours_sunday_holiday)) + ')'
                        # create/overwrite the rule in the temporary results
                        if amount != 0:
                            result[rule.code] = {
                                'sequence': rule.sequence,
                                'code': rule.code,
                                'name': rule_name,
                                'salary_rule_id': rule.id,
                                'contract_id': localdict['contract'].id,
                                'employee_id': localdict['employee'].id,
                                'amount': amount,
                                'quantity': qty,
                                'rate': rate,
                                'slip_id': payslip.id,
                            }
            line_vals += list(result.values())
        return line_vals
