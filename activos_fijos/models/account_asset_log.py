# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

class AccountMoveLog(models.Model):
    _name = 'account.asset.log'
    _description = 'Relacion de obras en curso'

    asset_id = fields.Many2one('account.asset', string='id', required=True, ondelete='cascade')
    asset_relation_id = fields.Many2one('account.asset', string='Activo', required=True)
    account = fields.Many2one('account.account', string='Cuenta', required=True)
    date = fields.Date('Fecha de impresion')
    asset_description = fields.Char('Etiqueta')
    mount = fields.Float('Monto')