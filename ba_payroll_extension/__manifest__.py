# -*- coding: utf-8 -*-
{
    'name': 'Payroll Extension',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': '',
    'description': """Payroll Customization""",
    "author": "Braincrew Apps",
    "website": 'http://www.braincrewapps.com',
    "license": "AGPL-3",
    'depends': ['analytic', 'hr_payroll', 'hr_holidays', 'hr_timesheet', 'l10n_ke_hr_payroll', 'hr_attendance'],
    'data': [
        'data/payroll_data.xml',
        'security/ir.model.access.csv',
        'report/hr_payroll_report_inh.xml',
        'wizard/monthly_bank_report_wizard_views.xml',
        'wizard/p10_report.xml',
        'wizard/p10_m_report.xml',
        'views/hr_payroll.xml',
        'views/res_partner_bank_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    "application": False,
}
