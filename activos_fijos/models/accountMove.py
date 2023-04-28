from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

class accountMove(models.Model):
    _inherit = 'account.move'

    updated_increment = fields.Float('updated increment', digits=(12,5))
    updated_item = fields.Float('updated item')
    value_ufv = fields.Float('ufv',digits=(12,5))
    date_ufv = fields.Date()
    net_worth_item = fields.Float()
    initial_ufv = fields.Float(string='UFV inicial',digits=(12,5))
    initial_date = fields.Date(string='Fecha inicial')
    factor = fields.Float(digits=(12,5))
    status_factor = fields.Char()
    historical_depreciation = fields.Float(string='Valor histórico')
    method = fields.Char()
    year_acumulated_depreciation = fields.Float()
    depreciation_initial = fields.Float(digits=(12,2))
    year_acumulated_depreciation_updated = fields.Float(digits=(12,2))
    aitb = fields.Float(digits=(12,5))
    no_depreciation = fields.Boolean(string="No depreciable")
    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        method = vals['method']
        if method == 'bolivian':
            missing_fields = set(
                ['asset_id', 'move_ref', 'amount', 'asset_remaining_value',
                 'asset_depreciated_value', 'updated_increment', 'updated_item',
                 'value_ufv', 'date_ufv','net_worth_item','initial_ufv', 'initial_date',
                 'factor','status_factor', 'historical_depreciation',
                 'year_acumulated_depreciation', 'depreciation_initial',
                 'year_acumulated_depreciation_updated', 'aitb']) - set(vals)
        else:
            missing_fields = set(
                ['asset_id', 'move_ref', 'amount',
                 'asset_remaining_value', 'asset_depreciated_value']) - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing {}').format(', '.join(missing_fields)))
        asset = vals['asset_id']
        account_analytic_id = asset.account_analytic_id
        analytic_tag_ids = asset.analytic_tag_ids
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount_currency = vals['amount']
        amount = current_currency._convert(amount_currency,
                                           company_currency, asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        if method == 'bolivian':
            updated_increment = vals['updated_increment']
            updated_item = vals['updated_item']
            value_ufv = vals['value_ufv']
            date_ufv = vals['date_ufv']
            net_worth_item = vals['net_worth_item']
            initial_ufv = vals['initial_ufv']
            initial_date = vals['initial_date']
            factor = vals['factor']
            status_factor = vals['status_factor']
            depreciation_initial = vals['depreciation_initial']
            historical_depreciation = vals['historical_depreciation']
            year_acumulated_depreciation = vals['year_acumulated_depreciation']
            year_acumulated_depreciation_updated = vals['year_acumulated_depreciation_updated']
            aitb = vals['aitb']
            no_depreciation = vals['no_depreciation']
        if (asset.original_move_line_ids and asset.original_move_line_ids[0].move_id.move_type
            in ['in_refund', 'out_refund']):
            amount = -amount
            amount_currency = -amount_currency

        if not no_depreciation:
            move_line_1 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': asset.account_depreciation_id.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)]
                if asset.asset_type == 'sale' else False,
                'currency_id': current_currency.id,
                'amount_currency': -amount_currency,
            }
            move_line_2 = {
                'name': asset.name,
                'partner_id': partner.id,
                'account_id': asset.account_depreciation_expense_id.id,
                'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type
                                                                 in ('purchase', 'expense') else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                    'purchase', 'expense') else False,
                'currency_id': current_currency.id,
                'amount_currency': amount_currency,
            }
        if method == 'bolivian':
            if status_factor == 'incremento':
                move_line_3 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_asset_id.id,
                    'credit': 0.0,
                    'debit': updated_increment or 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
                move_line_4 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_inflation_tenure_id.id,
                    'credit': updated_increment or 0.0,
                    'debit': 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
                if no_depreciation == False:
                    move_line_5 = {
                        'name': asset.name,
                        'partner_id': partner.id,
                        'account_id': asset.account_inflation_tenure_id.id,
                        'credit': 0.0,
                        'debit': aitb or 0.0,
                        'analytic_account_id': account_analytic_id.id if asset.asset_type
                                                                         in ('purchase', 'expense') else False,
                        'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                            'purchase', 'expense') else False,
                        'currency_id': current_currency.id,
                        'amount_currency': amount_currency,
                    }
                    move_line_6 = {
                        'name': asset.name,
                        'partner_id': partner.id,
                        'account_id': asset.account_depreciation_id.id,
                        'credit': aitb or 0.0,
                        'debit': 0.0,
                        'analytic_account_id': account_analytic_id.id if asset.asset_type
                                                                         in ('purchase', 'expense') else False,
                        'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                            'purchase', 'expense') else False,
                        'currency_id': current_currency.id,
                        'amount_currency': amount_currency,
                    }
            else:
                move_line_3 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_asset_id.id,
                    'credit': updated_increment or 0.0,
                    'debit': 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
                move_line_4 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_inflation_tenure_id.id,
                    'credit': 0.0,
                    'debit': updated_increment or 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
            if no_depreciation == False:
                move_line_5 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_inflation_tenure_id.id,
                    'credit': aitb or 0.0,
                    'debit': 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
                move_line_6 = {
                    'name': asset.name,
                    'partner_id': partner.id,
                    'account_id': asset.account_depreciation_id.id,
                    'credit': 0.0,
                    'debit': aitb or 0.0,
                    'analytic_account_id': account_analytic_id.id if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type in (
                        'purchase', 'expense') else False,
                    'currency_id': current_currency.id,
                    'amount_currency': amount_currency,
                }
        if method == 'bolivian':
            if no_depreciation == False:
                move_vals = {
                    'ref': vals['move_ref'],
                    'partner_id': partner.id,
                    'date': depreciation_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2), (0, 0, move_line_3),
                                 (0, 0, move_line_4), (0, 0, move_line_5), (0, 0, move_line_6)],
                    'asset_id': asset.id,
                    'asset_remaining_value': vals['asset_remaining_value'],
                    'asset_depreciated_value': vals['asset_depreciated_value'],
                    'amount_total': amount,
                    'name': '/',
                    'asset_value_change': vals.get('asset_value_change', False),
                    'move_type': 'entry',
                    'currency_id': current_currency.id,
                    'updated_increment': updated_increment,
                    'updated_item': updated_item,
                    'value_ufv': value_ufv,
                    'date_ufv': date_ufv,
                    'net_worth_item': net_worth_item,
                    'initial_ufv': initial_ufv,
                    'initial_date': initial_date,
                    'factor': factor,
                    'status_factor': status_factor,
                    'depreciation_initial': depreciation_initial,
                    'historical_depreciation': historical_depreciation,
                    'year_acumulated_depreciation': year_acumulated_depreciation,
                    'year_acumulated_depreciation_updated': year_acumulated_depreciation_updated,
                    'aitb': aitb
                }
            else:
                move_vals = {
                    'ref': vals['move_ref'],
                    'partner_id': partner.id,
                    'date': depreciation_date,
                    'journal_id': asset.journal_id.id,
                    'line_ids': [(0, 0, move_line_3),
                                 (0, 0, move_line_4)],
                    'asset_id': asset.id,
                    'asset_remaining_value': vals['asset_remaining_value'],
                    'asset_depreciated_value': vals['asset_depreciated_value'],
                    'amount_total': amount,
                    'name': '/',
                    'asset_value_change': vals.get('asset_value_change', False),
                    'move_type': 'entry',
                    'currency_id': current_currency.id,
                    'updated_increment': updated_increment,
                    'updated_item': updated_item,
                    'value_ufv': value_ufv,
                    'date_ufv': date_ufv,
                    'net_worth_item': net_worth_item,
                    'initial_ufv': initial_ufv,
                    'initial_date': initial_date,
                    'factor': factor,
                    'status_factor': status_factor,
                    'depreciation_initial': depreciation_initial,
                    'historical_depreciation': historical_depreciation,
                    'year_acumulated_depreciation': year_acumulated_depreciation,
                    'year_acumulated_depreciation_updated': year_acumulated_depreciation_updated,
                    'aitb': aitb
                }
        else:
            move_vals = {
                'ref': vals['move_ref'],
                'partner_id': partner.id,
                'date': depreciation_date,
                'journal_id': asset.journal_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                'asset_id': asset.id,
                'asset_remaining_value': vals['asset_remaining_value'],
                'asset_depreciated_value': vals['asset_depreciated_value'],
                'amount_total': amount,
                'name': '/',
                'asset_value_change': vals.get('asset_value_change', False),
                'move_type': 'entry',
                'currency_id': current_currency.id,
            }
        return move_vals

