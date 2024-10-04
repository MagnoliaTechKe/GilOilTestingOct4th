from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_branch = fields.Char(string="Bank Branch")
