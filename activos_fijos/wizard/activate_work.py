# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class AssetActivate(models.TransientModel):
    _name = 'activate.work'

    name = fields.Char(string='Nombre del activo')
    asset_id = fields.Many2one(string="Documento base", comodel_name='account.asset', required=True,
                               help="The asset to be modified by this wizard", ondelete="cascade", readonly=True)
    action = fields.Char(string='Acción', required=True, default='Activar Obra', readonly=True)
    activation_date = fields.Date(string='Fecha de Activación', required=True)
    reference_value = fields.Float(string='Valor de Referencia', required=True)
    # id_model = fields.Many2one('account.asset', string='id modelo')
    asset_model = fields.Many2one('account.asset', string='Modelo de Activo', domain=[('state', '=', 'model')])

    # @api.onchange('asset_model')
    # def _get_domain_asset_model(self):
    #     self.ensure_one()
    #     filters = self.env.user.filters_account_ids
    #     domain = []
    #     if filters:
    #         domain.append(('id', 'in', filters and filters.ids or False))
    #     return {'domain': {'account_asset_id': domain,
    #                        'account_depreciation_id': domain,
    #                        'account_depreciation_expense_id': domain,
    #                        'account_inflation_tenure_id': domain}}
    def activate(self):
        create_asset = self.env['account.asset'].create({
            'name': self.name,
            'currency_id': self.asset_id.currency_id.id,
            'company_id': self.asset_id.company_id.id,
            'asset_type': self.asset_id.asset_type,
            'method': self.asset_id.method,
            'method_number': self.asset_model.method_number,
            'method_period': self.asset_model.method_period,
            'acquisition_date': self.activation_date,
            'original_value': self.reference_value,
            'account_asset_id': self.asset_model.account_asset_id.id,
            'account_depreciation_id': self.asset_model.account_depreciation_id.id,
            'account_depreciation_expense_id': self.asset_model.account_depreciation_expense_id.id,
            'journal_id': self.asset_model.journal_id.id,
            'parent_id': self.asset_model.parent_id.id,
            'account_inflation_tenure_id': self.asset_model.account_inflation_tenure_id.id,
            'asset_model_id': self.asset_model.id,
            'model_id': self.asset_model.id,
            'no_depreciation': self.asset_model.no_depreciation,
            'no_depreciation_flag': self.asset_model.no_depreciation,
            'display_account_asset_id': True,
            'active_transformed': True, #Obra en curso concluido
            'relational_account_asset_id': self.asset_id.id, #Relacion con el activo base
        })
        # create_asset.validate()
        self.asset_id.active_transformed = True
        self.asset_id.relational_account_asset_id = create_asset.id
        self.asset_id.state = 'close'
        log_obj = self.env['account.asset.log']
        log_obj.create({
            'asset_id': create_asset.id,
            'asset_relation_id': self.asset_id.id,
            'account': self.asset_id.account_asset_id.id,
            'date': datetime.now(),
            'asset_description': self.asset_id.name,
            'mount': self.asset_id.original_value,
        })
        # return create_asset
        get_action = self.env['ir.actions.act_window']._for_xml_id('account_asset.action_account_asset_form')
        get_action['res_id'] = create_asset.id
        get_action['view_mode'] = 'form'
        get_action['target'] = 'main'
        get_action['context'] = {'default_id': create_asset.id}
        get_action['domain'] = [('id', '=', create_asset.id)]
        return get_action