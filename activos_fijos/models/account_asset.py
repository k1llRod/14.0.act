# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import datetime
from math import copysign

from odoo.tools.populate import compute


class accountAsset(models.Model):

    _inherit = 'account.asset'
    #_rec_name = 'codigo_activo'

    group_suffix = fields.Char()
    fixed_code = fields.Char()
    grupocontable_id = fields.Many2one(
                                    comodel_name='activos_fijos.grupocontable',
                                    string = 'Grupos contables'
    )
    @api.onchange('grupocontable_id')
    def meses_dep(self):
        self.vida_util = self.grupocontable_id.vida_util * 12
    vida_util = fields.Integer('Vida util en meses',compute='meses_dep')

    @api.depends(
        'original_value', 'salvage_value', 'already_depreciated_amount_import',
        'depreciation_move_ids.state',
        'depreciation_move_ids.amount_total',
        'depreciation_move_ids.reversal_move_id'
    )
    def _compute_value_residual(self):
        for record in self:
            posted = record.depreciation_move_ids.filtered(
                lambda m: m.state == 'posted' and not m.reversal_move_id
            )
            if posted:
                value_residual_bolivian = posted[0].net_worth_item
            else:
                value_residual_bolivian = record.original_value
            record.value_residual = (
                    value_residual_bolivian
            )

    def _compute_field(self):
        domain = self.env.ref('activos_fijos.ufv')
        return [('currency_id','=',domain.id)]

    currency_rate = fields.Many2one(
        comodel_name='res.currency.rate',
        string='UFV Inicial',
        domain=_compute_field
    )
    def ufv_today(self):
        domain = self.env.ref('activos_fijos.ufv')
        self.ufv_today_id = domain.id

    ufv_today_id = fields.Integer(compute=ufv_today)
    set_valor = fields.Date('UFV inicial', related='acquisition_date')
    valor = fields.Float('Valor UFV inicial', compute='compute_get_value_currency_ufv',
                         digits=(12,5))
    fecha = fields.Date('Fecha inicial', related='currency_rate.name', readonly=True)
    first_depreciation_date = fields.Date(related='acquisition_date')

    #Activos sin depreciacion
    no_depreciation = fields.Boolean(string="Sin Depreciación")
    no_depreciation_flag = fields.Boolean(string="Sin Depreciación", related='model_id.no_depreciation', readonly=True)
    asset_model_id = fields.Many2one(
        'account.asset',
        string="Modelo del Activo",
        store=True
    )
    no_update = fields.Boolean(string="Sin Actualización ni Depreciación")
    no_update_flag = fields.Boolean(
        string="Sin Actualización ni Depreciación",
        related='model_id.no_update',
        readonly=True)

    #Rodrigo
    work_in_progress = fields.Boolean(string="Obra en curso")
    work_in_progress_flag = fields.Boolean(string="Obra en curso", related='model_id.work_in_progress', readonly=True)
    active_transformed = fields.Boolean(string="Obra en curso concluido", readonly=True)

    @api.depends('set_valor')
    def compute_get_value_currency_ufv(self):
        ufv = self.env.ref('activos_fijos.ufv')
        for rec in self:
            if ufv.rate_ids.filtered(lambda l: l.name == rec.set_valor):
                rec.valor = ufv.rate_ids.filtered(lambda l: l.name == rec.set_valor).rate
                rec.first_depreciation_date = ufv.rate_ids.filtered(lambda l: l.name == rec.set_valor).name
                rec.initial_ufv_dinamic = rec.valor = ufv.rate_ids.filtered(lambda l: l.name == rec.set_valor).rate
                rec.initial_date_dinamic = ufv.rate_ids.filtered(lambda l: l.name == rec.set_valor).name
            else:
                rec.valor = 0
                rec.first_depreciation_date = rec.acquisition_date

            # value = rec.currency_rate.name
            # rate = rec.currency_rate.search([('currency_id','=',171),('name','=',rec.set_valor)])
            # rec.currency_rate = rate.id
            # rec.valor = rate.rate
    # first_depreciation_date = fecha
    # ufv.rate_ids
    def get_default_value(self):
        variable = self.env['res.currency.rate'].search([],limit=1,order='name DESC')
        return variable

    currency_rate_value = fields.Many2one(
        comodel_name='res.currency.rate',
        string='Fecha UFV final',
        domain=_compute_field,
        default=get_default_value
    )
    def get_fecha_ufv_actual(self):
        hoy = date.today()
        variable = self.env['res.currency.rate'].search([('name','=',hoy)], limit=1, order='name DESC')
        return variable.name

    def get_valor_ufv_actual(self):
        hoy = date.today()
        ufv = self.ufv_today_id
        variable = self.env['res.currency.rate'].search([('currency_id','=',ufv), ('name','=', hoy)])
        return variable.rate

    def valor_actual(self):
        hoy = date.today()
        ufv = self.ufv_today_id
        variable = self.env['res.currency.rate'].search([('currency_id','=',ufv),('name','=',hoy)])
        self.fecha_ufv_actual_create = variable.name

    fecha_ufv_actual_create = fields.Char( compute=valor_actual)

    valor_ufv_actual_create = fields.Float('valor_ufv_actual_create', default=get_valor_ufv_actual, readonly=True)

    def valor_ufv_write(self):
        for r in self:
            hoy = date.today()
            ufv = r.ufv_today_id
            #('id', '=', '190')
            variable = r.env['res.currency.rate'].search([('currency_id','=',ufv), ('name','=', hoy)])
            if not variable:
                r.env.user.notify_danger('No existe registro de moneda UFV, para la fecha actual')
            else:
                r.env.user.notify_success('UFV actualizada')
            r.valor_ufv_actual = variable.rate
            r.fecha_ufv_actual = variable.name

    fecha_ufv_actual = fields.Date(compute=valor_ufv_write, readonly=True)
    valor_ufv_actual = fields.Float(compute=valor_ufv_write, readonly=True, digits=(12,5))



    def incremento_actualizacion(self):
        self.incremento_actualizacion = self.depreciado_historico * ((self.valor_ufv_actual/self.valor)-1)

    incremento_actualizacion = fields.Float(string="Incremento por actualización", compute=incremento_actualizacion)

    def _actualizado(self):
        self.actualizado = self.depreciado_historico * (self.valor_ufv_actual/1)
    actualizado = fields.Float('Actualizado',compute=_actualizado)

    fecha_inicial = fields.Date('Fecha inicial', related='currency_rate.name')

    #fecha_final = fields.Date('Fecha final', related='currency_rate_value.name')

    def tiempo_consumido_meses(self):
        fecha_actual = date.today()
        for r in self:
            if(fecha_actual and self.first_depreciation_date):
                days = fields.Date.from_string(fields.Date.from_string(fecha_actual)) - fields.Date.from_string(self.first_depreciation_date)
                r.meses_consumidos = round(days.days / 30)
            else:
                 r.meses_consumidos = 0

    meses_consumidos = fields.Integer(string='Meses consumidos',compute='tiempo_consumido_meses')

    def tiempo_consumido_dias(self):
        fecha_actual = date.today()
        for r in self:
            if(fecha_actual and self.first_depreciation_date):
                days = fields.Date.from_string(fields.Date.from_string(fecha_actual)) - fields.Date.from_string(self.first_depreciation_date)
                r.dias_consumidos = days.days
            else:
                r.dias_consumidos = 0

    dias_consumidos = fields.Integer(string='Dias consumidos',compute='tiempo_consumido_dias')

    def saldo_restante(self):
        self.saldo = self.method_number - self.meses_consumidos

    saldo = fields.Integer('Saldo de vida para el siguiente periodo', compute='saldo_restante')

    def _actualizar_activo(self):
        #actualizar = self.depreciado_historico(self.valor_ufv_final / self.valor)
        self.valor_activo_actualizado = self.depreciado_historico * (self.valor_ufv_actual / self.valor)

    valor_activo_actualizado = fields.Float(string='Activo actualizado',compute=_actualizar_activo)

    def _dep_anual(self):
        self.dep_anual = (self.valor_activo_actualizado / self.vida_util) * (self.meses_consumidos)

    dep_anual = fields.Float(string='Depreciación anual',compute='_dep_anual')

    #DEFINIR MODIFICACION DE FUNCION PARA TABLA DE DEPRECIACION

    # def action_depreciacion(self):
    #     tabla = self.env['activos_fijos.tabla_depreciacion']
    #     tabla_id = tabla.create({
    #         'name': self.name,
    #         'fecha_depreciacion':self.fecha_inicial,
    #         'ufv_inicial':self.valor,
    #         'fecha_final': self.fecha_final,
    #         'ufv_final': self.valor_ufv_final,
    #         'depreciacion': self.dep_anual,
    #         'activo_id': self.id
    #     })

    def fecha_adquiscion_ufv(self):
        var = date.today()
        self.fecha = var

    #fecha = fields.Char('prueba',compute=fecha_adquiscion_ufv)
    historical_depreciation_auxiliar = fields.Float()
    depreciation_initial_auxiliar = fields.Float()

    #Cuentas agregadas
    account_inflation_tenure_id = fields.Many2one('account.account','Ajuste por inflación y tenencia de bienes')


    #Datos para backup

    amount_massive = fields.Float('Valor histórico actualizado')
    date_massive = fields.Date('Ultima fecha de depreciación')

    def months_historical_consumed(self):
        fecha_actual = date.today()
        for r in self:
            if (fecha_actual and r.first_depreciation_date and r.date_massive):
                days = fields.Date.from_string(fields.Date.from_string(r.date_massive)) - fields.Date.from_string(self.first_depreciation_date)
                r.historical_time_consumed = round(days.days / 30)
            else:
                r.historical_time_consumed = 0

    historical_time_consumed = fields.Integer('Tiempo histórico consumido',compute=months_historical_consumed ,readonly=True)
    accumulated_depreciation = fields.Float('Depreciación acumulada')

    def values_initial(self):
        for r in self:
            r.initial_ufv_dinamic = r.valor
            r.initial_date_dinamic = r.first_depreciation_date

    initial_ufv_dinamic = fields.Float('initial ufv dinamic', compute='values_initial')
    initial_date_dinamic = fields.Date('Date ufv dinamic', compute='values_initial')

    # Modificar select de metodos de depreciacion
    method = fields.Selection(selection_add=[('bolivian', 'index UFV')],
                              default='bolivian')

    method_number = fields.Integer(string='Number of Depreciations', readonly=True,
                                   states={'draft': [('readonly', False)], 'model': [('readonly', False)]}, default=5,
                                   help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Selection([('1', 'Months'), ('12', 'Years')], string='Number of Months in a Period',
                                     readonly=True,
                                     states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
                                     help="The amount of time between two depreciations")
    method_progress_factor = fields.Float(string='Declining Factor', readonly=True, default=0.0,
                                          states={'draft': [('readonly', False)], 'model': [('readonly', False)]})


    #Modificar funciones

    def _compute_board_amount(self, computation_sequence, residual_amount, total_amount_to_depr, max_depreciation_nb, starting_sequence, depreciation_date, sw):
        if sw == 0 and self.amount_massive == 0:
            year_acumulated_depreciation = 0
        else:
            if(sw == 0 and self.amount_massive > 0):
                year_acumulated_depreciation = self.depreciation_initial_auxiliar
            else:
                year_acumulated_depreciation = self.depreciation_initial_auxiliar
        #initial_deprecation = 0

        historical_depreciation = self.historical_depreciation_auxiliar
        depreciation_initial = self.depreciation_initial_auxiliar
        amount = 0
        updated_increment = 0
        updated_item = 0
        aitb = 0

        for rec in self:
            if rec.amount_massive > 0 and sw==0:
                initial_date = rec.date_massive
                ufv = rec.ufv_today_id
                ufv_massive = rec.env['res.currency.rate'].search([('currency_id','=',ufv), ('name','=',initial_date)])
                initial_ufv = ufv_massive.rate
            else:
                initial_ufv = rec.initial_ufv_dinamic
                initial_date = rec.initial_date_dinamic

        factor = 0
        year_acumulated_depreciation_updated = 0
        net_worth_item = 0
        minimum_deprecation_range = self.salvage_value

        global valueufv, date_ufv
        if computation_sequence == max_depreciation_nb and self.method != 'bolivian':
            # last depreciation always takes the asset residual amount
            amount = residual_amount
        else:
            if self.method in ('bolivian'):
                if sw == 0:

                    if int(self.method_period) == 1:
                        month_ufv_historial = depreciation_date
                        max_day_in_month = calendar.monthrange(month_ufv_historial.year, month_ufv_historial.month)[1]
                        month_ufv_historial = depreciation_date.replace(day=max_day_in_month)
                        period = int(self.method_period)
                    else:
                        month_ufv_historial = depreciation_date
                        max_day_in_month = calendar.monthrange(month_ufv_historial.year, int(self.method_period))[1]
                        month_ufv_historial = depreciation_date.replace(day=max_day_in_month, month=int(self.method_period))
                        month_actual = depreciation_date.month
                        period = (12 - month_actual) + 1

                else:
                    month_ufv_historial = depreciation_date
                    month_actual = depreciation_date.month
                    if(int(self.method_period) == 12):
                        period = 12
                        if (computation_sequence == max_depreciation_nb and (12 - (12 - self.first_depreciation_date.month + 1)>0)):
                            period = 12 - (12 - self.first_depreciation_date.month + 1)
                            month_ufv_historial = depreciation_date
                            month_ufv_historial = month_ufv_historial.replace(day=1, month=period)
                            max_day_in_month = calendar.monthrange(month_ufv_historial.year, month_ufv_historial.month)[1]
                            month_ufv_historial = month_ufv_historial.replace(day=max_day_in_month)
                    else:
                        period = 1



                ufv = self.ufv_today_id
                variable = self.env['res.currency.rate'].search([('currency_id','=',ufv), ('name','=',month_ufv_historial)])
                valueufv = variable.rate
                date_ufv = variable.name
                #una_fecha = '2019/01/01'
                #fecha_dt = datetime.strptime(una_fecha, '%d/%m/%Y')

                if initial_ufv > 0:
                    factor = ((valueufv / initial_ufv) - 1)
                else:
                    factor = 0
                aitb = year_acumulated_depreciation * factor

                days_consumed = fields.Date.from_string(
                    fields.Date.from_string(month_ufv_historial)) - fields.Date.from_string(
                    self.first_depreciation_date) #dias consumidos
                month_consumed = round(days_consumed.days / 30) #meses consumidos
                updated_increment = historical_depreciation *(factor)    #incremento por actualizacion
                updated_item = historical_depreciation + updated_increment #valor actualizado
                #depreciation = ((updated_item - minimum_deprecation_range)/ max_depreciation_nb) * (1) #depreciacion del ejercicio
                if self.method_period == '12':
                    if self.method_number > 0:
                        max_depreciation_nb = self.method_number
                    else:
                        max_depreciation_nb = 1
                    depreciation = ((updated_item - minimum_deprecation_range) / (max_depreciation_nb * 12)) * period
                else:
                    depreciation = ((updated_item - minimum_deprecation_range) / max_depreciation_nb) * period
                year_acumulated_depreciation_updated =  aitb + depreciation_initial + depreciation
                month_december = month_ufv_historial.month  # mes de diciembre
                net_worth_item = updated_item - year_acumulated_depreciation_updated #valor neto
                self.historical_depreciation_auxiliar = updated_item
                self.depreciation_initial_auxiliar = year_acumulated_depreciation_updated

                #date_next = month_ufv_historial + timedelta(1)
                date_next = month_ufv_historial
                var = self.env['res.currency.rate'].search([('currency_id','=',ufv), ('name','=',date_next)])
                self.initial_ufv_dinamic = var.rate
                self.initial_date_dinamic = var.name
                #year_acumulated_depreciation = carry
                if(sw == 1):
                    carry = depreciation
                if depreciation <= 0:
                    depreciation = 0.0
                amount = depreciation #depreciacion
            if self.method in ('degressive', 'degressive_then_linear'):
                amount = residual_amount * self.method_progress_factor
            if self.method in ('linear', 'degressive_then_linear'):
                nb_depreciation = max_depreciation_nb - starting_sequence
                if self.prorata:
                    nb_depreciation -= 1
                linear_amount = min(total_amount_to_depr / nb_depreciation, residual_amount)
                if self.method == 'degressive_then_linear':
                    amount = max(linear_amount, amount)
                else:
                    amount = linear_amount

        if(self.method == 'bolivian'):
            #sw = 1
            return amount, updated_increment, updated_item, valueufv,date_ufv, net_worth_item, initial_ufv, initial_date, factor, historical_depreciation, year_acumulated_depreciation, sw, depreciation_initial, year_acumulated_depreciation_updated, aitb
        else:
            return amount

    def compute_depreciation_board(self):
        self.ensure_one()
        no_depreciation = self.no_depreciation #AGREGAR CAMPOS PARA ACTIVOS QUE NO DEPRECIAN
        amount_change_ids = self.depreciation_move_ids.filtered(lambda x: x.asset_value_change and not x.reversal_move_id).sorted(key=lambda l: l.date)
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted' and not x.asset_value_change and not x.reversal_move_id).sorted(key=lambda l: l.date)
        already_depreciated_amount = sum([m.amount_total for m in posted_depreciation_move_ids])
        depreciation_number = self.method_number
        if self.no_depreciation == True: #CONDICION PARA CAMBIAR EL NUMERO DE DEPRECIACIONES
            fecha_actual = datetime.today()
            depreciation_number = (((fecha_actual.year - self.first_depreciation_date.year)*12) + fecha_actual.month - self.first_depreciation_date.month) + 1
        if self.prorata:
            depreciation_number += 1
        if self.method_period == '12':
            if self.first_depreciation_date.month > 1:
                depreciation_number += 1
        if(self.amount_massive > 0):
            days = fields.Date.from_string(fields.Date.from_string(self.date_massive)) - fields.Date.from_string(
                self.first_depreciation_date)
            historical_days_consumed = round(days.days / 30)
            starting_sequence = historical_days_consumed - 1
        else:
            starting_sequence = 0
        if self.method != 'bolivian':
            amount_to_depreciate = self.value_residual + sum([m.amount_total for m in amount_change_ids])
        else:
            if self.salvage_value < self.original_value:
                amount_to_depreciate = self.original_value
            else:
                amount_to_depreciate = self.value_residual
        salvage_value = self.salvage_value
        depreciation_date = self.first_depreciation_date
        commands = [(2, line_id.id, False) for line_id in self.depreciation_move_ids.filtered(lambda x: x.state == 'draft')]
        newlines = self._recompute_board(depreciation_number, starting_sequence, amount_to_depreciate, depreciation_date, already_depreciated_amount, amount_change_ids, no_depreciation,salvage_value)
        newline_vals_list = []
        for newline_vals in newlines:
            # no need of amount field, as it is computed and we don't want to trigger its inverse function
            del(newline_vals['amount_total'])
            newline_vals_list.append(newline_vals)
        new_moves = self.env['account.move'].create(newline_vals_list)
        for move in new_moves:
            commands.append((4, move.id))
        return self.write({'depreciation_move_ids': commands})

    def _recompute_board(self, depreciation_number, starting_sequence, amount_to_depreciate, depreciation_date,
                         already_depreciated_amount, amount_change_ids, no_depreciation, salvage_value):
        self.ensure_one()
        residual_amount = amount_to_depreciate
        self.historical_depreciation_auxiliar = residual_amount
        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        move_vals = []
        prorata = self.prorata and not self.env.context.get("ignore_prorata")
        if amount_to_depreciate != 0.0:
            sw = 0
            historical_depreciation = 0
            c = 0
            var = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted')
            if(self.accumulated_depreciation > 0):
                if(range(starting_sequence, depreciation_number)):
                    self.depreciation_initial_auxiliar = self.accumulated_depreciation
                    self.historical_depreciation_auxiliar = self.amount_massive
                    date_aux = self.date_massive
                    date_massive_next = date_aux + timedelta(1)
                    max_day_in_month = calendar.monthrange(date_massive_next.year, date_massive_next.month)[1]
                    date_massive_next = date_massive_next.replace(day=max_day_in_month)
                    depreciation_date = date_massive_next
                    cc = starting_sequence
                else:
                    var = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted')
                    if not (var):
                        move_ref = self.name + ' (%s/%s)' % (self.method_number, self.method_number)
                        vals = {
                            'amount': 0.0,
                            'asset_id': self,
                            'move_ref': move_ref,
                            'date': self.date_massive,
                            'historical_depreciation': self.amount_massive,
                            'updated_increment': 0.0,
                            'updated_item': 0.0,
                            'value_ufv': 0.0,
                            'date_ufv': self.date_massive,
                            'factor': 0.0,
                            'status_factor': 0.0,
                            'year_acumulated_depreciation': 0.0,
                            'year_acumulated_depreciation_updated': 0.0,
                            'net_worth_item': self.amount_massive,
                            'initial_ufv': 0,
                            'initial_date': self.acquisition_date,
                            'depreciation_initial': self.accumulated_depreciation,
                            'aitb': 0.0,
                            'method': self.method,
                            'asset_remaining_value': float_round(residual_amount,
                                                                 precision_rounding=self.currency_id.rounding),
                            'asset_depreciated_value': 0.0,
                            'no_depreciation': self.no_depreciation,
                            'salvage_value': self.salvage_value,
                         }
                        move_vals.append(self.env['account.move']._prepare_move_for_asset_depreciation(vals))
            else:
                self.depreciation_initial_auxiliar = 0
                var = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted')

            accounting_record = self.depreciation_move_ids.filtered(lambda m: m.state == 'posted' and not m.reversal_move_id)
            order_accounting_record = sorted(accounting_record,key=lambda x: x['id'],reverse=False)
            len_accounting_record = len(order_accounting_record)
            #v = datetime.strptime(var[0].date_ufv, "%Y-%m-%d")

            for asset_sequence in range(starting_sequence + 1, depreciation_number + 1):
                if(self.amount_massive > 0 and sw == 0):
                    cc = starting_sequence + 1
                    c = 1

                while amount_change_ids and amount_change_ids[0].date <= depreciation_date:
                    if not amount_change_ids[0].reversal_move_id:
                        residual_amount -= amount_change_ids[0].amount_total
                        amount_to_depreciate -= amount_change_ids[0].amount_total
                        already_depreciated_amount += amount_change_ids[0].amount_total
                    amount_change_ids[0].write({
                        'asset_remaining_value': float_round(residual_amount,
                                                             precision_rounding=self.currency_id.rounding),
                        'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                    })
                    amount_change_ids -= amount_change_ids[0]
                if self.method == 'bolivian':
                    amount,updated_increment,updated_item, valueufv, date_ufv, net_worth_item, initial_ufv, initial_date, factor, historical_depreciation, year_acumulated_depreciation,sw, depreciation_initial, year_acumulated_depreciation_updated, aitb = self._compute_board_amount(asset_sequence, residual_amount, amount_to_depreciate, depreciation_number, starting_sequence, depreciation_date, sw)

                else:
                    amount = self._compute_board_amount(asset_sequence, residual_amount, amount_to_depreciate, depreciation_number, starting_sequence, depreciation_date, sw)
                prorata_factor = 1
                if c > 0:
                    move_ref = self.name + ' (%s/%s)' % (prorata and asset_sequence + 1 or asset_sequence, self.method_number)
                    if self.no_depreciation == True:
                        move_ref = self.name + ' (%s)' % (prorata and asset_sequence - 1 or asset_sequence)
                else:
                    move_ref = self.name + ' (%s/%s)' % (prorata and asset_sequence - 1 or asset_sequence, self.method_number)
                    if self.no_depreciation == True:
                        move_ref = self.name + ' (%s)' % (prorata and asset_sequence - 1 or asset_sequence)
                if prorata and asset_sequence == 1:
                    move_ref = self.name + ' ' + _('(prorata entry)')
                    first_date = self.prorata_date
                    if int(self.method_period) % 12 != 0:
                        month_days = calendar.monthrange(first_date.year, first_date.month)[1]
                        days = month_days - first_date.day + 1
                        prorata_factor = days / month_days
                    else:
                        total_days = (depreciation_date.year % 4) and 365 or 366
                        days = (self.company_id.compute_fiscalyear_dates(first_date)['date_to'] - first_date).days + 1
                        prorata_factor = days / total_days
                amount = self.currency_id.round(amount * prorata_factor)
                if asset_sequence == depreciation_number and (12 - (12 - self.first_depreciation_date.month + 1) > 0) and no_depreciation != True:
                    move_ref = self.name + ' ' + _('(prorata entry)')
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    if(self.method != 'bolivian'):
                        continue
                residual_amount -= amount
                method = self.method
                status_factor = 'incremento'
                if self.method == 'bolivian':
                    residual_amount = net_worth_item
                    if -1 < factor < 0:
                        factor = factor *(-1)
                        updated_increment = updated_increment * (-1)
                        aitb = aitb * (-1)
                        status_factor = 'decremento'

                    if not no_depreciation:
                        vals = {
                            'amount': amount,
                            'asset_id': self,
                            'move_ref': move_ref,
                            'date': depreciation_date,
                            'historical_depreciation': historical_depreciation,
                            'updated_increment': updated_increment,
                            'updated_item': updated_item,
                            'value_ufv': valueufv,
                            'date_ufv': date_ufv,
                            'factor': factor,
                            'status_factor': status_factor,
                            'year_acumulated_depreciation': year_acumulated_depreciation,
                            'year_acumulated_depreciation_updated': year_acumulated_depreciation_updated,
                            'net_worth_item': net_worth_item,
                            'initial_ufv': initial_ufv,
                            'initial_date': initial_date,
                            'depreciation_initial': depreciation_initial,
                            'aitb': aitb,
                            'method': method,
                            'asset_remaining_value': float_round(
                                residual_amount,
                                precision_rounding=self.currency_id.rounding),
                            'asset_depreciated_value': amount,
                            'no_depreciation': no_depreciation,
                            'salvage_value': self.salvage_value,
                        }
                    else: #DICCIONARIO PARA ARMAR EL ACTIVO SIN DEPRECIACION
                        vals = {
                            'amount': amount,
                            'asset_id': self,
                            'move_ref': move_ref,
                            'date': depreciation_date,
                            'historical_depreciation': historical_depreciation,
                            'updated_increment': updated_increment,
                            'updated_item': updated_item,
                            'value_ufv': valueufv,
                            'date_ufv': date_ufv,
                            'factor': factor,
                            'status_factor': status_factor,
                            'year_acumulated_depreciation': 0.0,
                            'year_acumulated_depreciation_updated': 0.0,
                            'net_worth_item': updated_item,
                            'initial_ufv': initial_ufv,
                            'initial_date': initial_date,
                            'depreciation_initial': 0.0,
                            'aitb': 0.0,
                            'method': method,
                            'asset_remaining_value': float_round(
                                residual_amount,
                                precision_rounding=self.currency_id.rounding),
                            'asset_depreciated_value': 0.0,
                            'no_depreciation': no_depreciation,
                            'salvage_value': self.salvage_value,
                        }
                else:
                    vals = {
                        'amount': amount,
                        'asset_id': self,
                        'move_ref': move_ref,
                        'date': depreciation_date,
                        'method':method,
                        'asset_remaining_value': float_round(residual_amount,
                                                             precision_rounding=self.currency_id.rounding),
                        'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                    }

                if self.method == 'bolivian' and factor > 0:
                    sw0 =0
                    verify_posted = self.depreciation_move_ids.filtered(lambda x: x.state == 'posted')
                    for r in verify_posted:
                        if(r.date_ufv == date_ufv):
                            sw0 = 1
                    if sw0!=1:
                        move_vals.append(self.env['account.move']._prepare_move_for_asset_depreciation(vals))

                if self.method != 'bolivian':
                    move_vals.append(self.env['account.move']._prepare_move_for_asset_depreciation(vals))
                    depreciation_date = depreciation_date + relativedelta(months=+int(self.method_period))
                    # datetime doesn't take into account that the number of days is not the same for each month
                    if int(self.method_period) % 12 != 0:
                        max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                        depreciation_date = depreciation_date.replace(day=max_day_in_month)

                if int(self.method_period) % 12 != 0:
                    depreciation_date = depreciation_date + relativedelta(months=+int(self.method_period))
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)
                    sw = 1
                if int(self.method_period) == 12:
                    depreciation_date = depreciation_date + relativedelta(months=+int(self.method_period))
                    depreciation_date = depreciation_date.replace(month=12)
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)
                    sw = 1
        else:
            if amount_to_depreciate == 0.0 and self.original_value >0:
                move_ref = self.name + ' (%s/%s)' % (self.method_number, self.method_number)
                vals = {
                    'amount': self.original_value,
                    'asset_id': self,
                    'move_ref': move_ref,
                    'date': depreciation_date,
                    'historical_depreciation': self.original_value,
                    'updated_increment': 0.0,
                    'updated_item': 0.0,
                    'value_ufv': 0,
                    'date_ufv': depreciation_date,
                    'factor': 0.0,
                    'status_factor': 0.0,
                    'year_acumulated_depreciation': 0.0,
                    'year_acumulated_depreciation_updated': 0.0,
                    'net_worth_item': self.book_value,
                    'initial_ufv': 0.0,
                    'initial_date': depreciation_date,
                    'depreciation_initial': 0.0,
                    'aitb': 0.0,
                    'method': self.method,
                    'asset_remaining_value': float_round(
                        residual_amount,
                        precision_rounding=self.currency_id.rounding),
                    'asset_depreciated_value': 0.0,
                    'no_depreciation': no_depreciation,
                    'no_update': self.no_update,
                    'salvage_value': self.salvage_value,
                }
                if not amount_to_depreciate < 0:
                    move_vals.append(self.env['account.move']._prepare_move_for_asset_depreciation(vals))
        return move_vals

    #campos extra auxiliares
    name_model = fields.Char("Grupo contable", related="model_id.name")

    codigo_activo = fields.Char('Codigo del activo')
    secuencia = fields.Char('Secuencia')

    #@api.onchange('group_suffix')
    def _codigo_activo(self, group_suffix,fixed_code):
        codigo = fixed_code + str(group_suffix) + '-' + str(self.secuencia)
        self.codigo_activo = codigo
    def _account_analytic(self, account_analytic):
        self.account_analytic_id = account_analytic

    @api.model
    def create(self, vals):
        vals['secuencia'] = self.env['ir.sequence'].next_by_code('account.asset')
        vals['group_suffix'] = self.group_suffix
        #vals['first_depreciation_date'] = self.acquisition_date
        #account_analytic = vals['account_analytic_id']
        result = super(accountAsset, self).create(vals)
        if 'codigo_activo' in vals:
            if not(vals['codigo_activo'] or self.codigo_activo) :
                group_suffix = result.account_asset_id.asset_model.group_suffix
                fixed_code = result.account_asset_id.asset_model.fixed_code #codigo general
                if not group_suffix:
                    group_suffix = '00'
                if not fixed_code:
                    fixed_code = 'AF'
                result._codigo_activo(group_suffix,fixed_code)
        else:
            if not self.codigo_activo:
                group_suffix = result.account_asset_id.asset_model.group_suffix
                fixed_code = result.account_asset_id.asset_model.fixed_code  # codigo general
                if not group_suffix:
                    group_suffix = '00'
                if not fixed_code:
                    fixed_code = 'AF'
                result._codigo_activo(group_suffix, fixed_code)
        #result.model_id.account_analytic_id = account_analytic
        #account_analytic = result.account_analytic_id
        #result._account_analytic(account_analytic)
        result.first_depreciation_date = result.acquisition_date
        return result
    hr_employee_id = fields.Many2one('hr.employee','Encargado', track_visibility='always')
    #Rodrigo
    #Activos fijo de origen
    account_asset_original_ids = fields.One2many('account.asset.log','asset_id', 'Activo fijo de origen', ondelete='cascade')
    #Valor auxiliar para el calculo del valor de referencia
    value_reference = fields.Float('Valor de referencia', store=True)
    #Relacion con el nuevo activo fijo
    relational_account_asset_id = fields.Many2one('account.asset', 'Activo fijo relacionado')
    #Boton transformar activar obra
    def action_activate_asset(self):
        val_min = sorted(self.depreciation_move_ids.filtered(lambda x: x.state == 'posted'), key=lambda y: y.id)
        if self.state == 'open' and val_min:
            for val in self:
                value = val.value_residual
                new_wizard = self.env['activate.work'].create({
                    'asset_id': val.id,
                    'activation_date': datetime.now(),
                    'asset_model': False,
                    # 'id_model': val.model_id.id,
                    # 'asset_model': val.model_id.id,
                    'reference_value': val.value_reference,
                })
        else:
            raise UserError(_('El activo fijo no se encuentra en estado "En proceso" o no tiene registros publicados.'))

        return {
            'name': _('Activate asset'),
            'view_mode': 'form',
            'res_model': 'activate.work',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    #Automata
    def automata(self):
        depreciation = self.env['account.asset'].search([('original_value','>','0')]).filtered(lambda m: m.method == 'bolivian')
        for record in depreciation:
            var = record.compute_depreciation_board()

    @api.constrains('depreciation_move_ids')
    def _check_depreciations(self):
        for record in self:
            if record.state == 'open' and record.depreciation_move_ids and not record.currency_id.is_zero(record.depreciation_move_ids.filtered(lambda x: not x.reversal_move_id).sorted(lambda x: (x.date, x.id))[-1].asset_remaining_value):
                c = 1
                #raise UserError(_("The remaining value on the last depreciation line must be 0"))


    def validate(self):
        fields = [
            'method',
            'method_number',
            'method_period',
            'method_progress_factor',
            'salvage_value',
            'original_move_line_ids',
        ]
        ref_tracked_fields = self.env['account.asset'].fields_get(fields)
        self.write({'state': 'open'})
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.method == 'linear':
                del (tracked_fields['method_progress_factor'])
            dummy, tracking_value_ids = asset._message_track(tracked_fields, dict.fromkeys(fields))
            asset_name = {
                'purchase': (_('Asset created'), _('An asset has been created for this move:')),
                'sale': (_('Deferred revenue created'), _('A deferred revenue has been created for this move:')),
                'expense': (_('Deferred expense created'), _('A deferred expense has been created for this move:')),
            }[asset.asset_type]
            msg = asset_name[1] + ' <a href=# data-oe-model=account.asset data-oe-id=%d>%s</a>' % (asset.id, asset.name)
            asset.message_post(body=asset_name[0], tracking_value_ids=tracking_value_ids)
            for move_id in asset.original_move_line_ids.mapped('move_id'):
                move_id.message_post(body=msg)
            if not asset.depreciation_move_ids:
                asset.compute_depreciation_board()
            #asset._check_depreciations()


    #ELIMINACION Y VENTA DE ACTIVOS FIJOS

    def set_to_close(self, invoice_line_id, date=None):
        self.ensure_one()
        disposal_date = date or fields.Date.today()
        if invoice_line_id and self.children_ids.filtered(lambda a: a.state in ('draft', 'open') or a.value_residual > 0):
            raise UserError(_("You cannot automate the journal entry for an asset that has a running gross increase. Please use 'Dispose' on the increase(s)."))
        full_asset = self + self.children_ids
        move_ids = full_asset._get_disposal_moves([invoice_line_id] * len(full_asset), disposal_date)
        full_asset.write({'state': 'close'})
        if move_ids:
            return self._return_disposal_view(move_ids)

    def _get_disposal_moves(self, invoice_line_ids, disposal_date):
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': current_currency.id,
                'amount_currency': -asset.value_residual,
            })

        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_id in zip(self, invoice_line_ids):
            posted_moves = asset.depreciation_move_ids.filtered(lambda x: (
                    not x.reversal_move_id
                    and x.state == 'posted'
            ))
            if posted_moves and disposal_date < max(posted_moves.mapped('date')):
                if invoice_line_id:
                    raise UserError(
                        'There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                else:
                    raise UserError('There are depreciation posted in the future, please revert them.')
            account_analytic_id = asset.account_analytic_id
            analytic_tag_ids = asset.analytic_tag_ids
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.state == 'draft')
            old_values = {
                'method_number': asset.method_number,
            }

            # Remove all unposted depr. lines
            commands = [(2, line_id.id, False) for line_id in unposted_depreciation_move_ids]

            # Create a new depr. line with the residual amount and post it
            asset_sequence = len(asset.depreciation_move_ids) - len(unposted_depreciation_move_ids) + 1

            #initial_amount = asset.original_value #valor original
            initial_amount = max(asset.depreciation_move_ids.filtered(lambda x: x.state =='posted')).updated_item;
            initial_account = asset.original_move_line_ids.account_id if len(asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
            #depreciation_moves = asset.depreciation_move_ids.filtered(lambda r: r.state == 'posted' and not (r.reversal_move_id and r.reversal_move_id[0].state == 'posted'))
            #depreciated_amount = copysign(sum(depreciation_moves.mapped('amount_total')) + asset.already_depreciated_amount_import,-initial_amount,)#monto total depreciacion
            depreciated_amount = -(max(asset.depreciation_move_ids.filtered(lambda x: x.state=='posted')).year_acumulated_depreciation_updated)

            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(invoice_line_id.price_subtotal, -initial_amount) #monto de factura
            invoice_account = invoice_line_id.account_id
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account),
                          (invoice_amount, invoice_account), (difference, difference_account)]
            if not invoice_line_id:
                del line_datas[2]
            vals = {
                'asset_id': asset.id,
                'ref': asset.name + ': ' + (_('Disposal') if not invoice_line_id else _('Sale')),
                'asset_remaining_value': 0,
                'asset_depreciated_value': max(asset.depreciation_move_ids.filtered(lambda x: x.state == 'posted'),
                                               key=lambda x: x.date,
                                               default=self.env['account.move']).asset_depreciated_value,
                'date': disposal_date,
                'journal_id': asset.journal_id.id,
                'line_ids': [get_line(asset, amount, account) for amount, account in line_datas if account],
            }
            commands.append((0, 0, vals))
            asset.write({'depreciation_move_ids': commands, 'method_number': asset_sequence})
            tracked_fields = self.env['account.asset'].fields_get(['method_number'])
            changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
            if changes:
                asset.message_post(body=_('Asset sold or disposed. Accounting entry awaiting for validation.'),
                                   tracking_value_ids=tracking_value_ids)
            move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids

    def star_account_asset(self):
        for product in self:
            product.validate()


    #MODIFICACION DE VENTA O ELIMINACION DE ACTIVOS FIJOS

    def action_set_to_close(self):
        """ Returns an action opening the asset pause wizard."""
        self.ensure_one()
        new_wizard = self.env['account.asset.sell'].create({
            'asset_id': self.id,
        })
        return {
            'name': _('Sell Asset'),
            'view_mode': 'form',
            'res_model': 'account.asset.sell',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
        }

    def accounting_entry_depreciation(self):
        asset_total = self.env['account.asset'].search([('original_value','>','0')]).filtered(lambda m: m.method == 'bolivian')
        for r in asset_total:
            for s in r.depreciation_move_ids.filtered(lambda m: m.state == 'draft').sorted(lambda x: (x.date, x.id)):
                s.action_post()

    def select_accounting_entry_depreciation(self):
        asset_account = self.depreciation_move_ids
        for asset in asset_account:
            if(asset.state == 'draft'):
                asset.action_post()

    def select_depreciation_account_assets(self):
        for asset in self:
            asset.compute_depreciation_board();

    def action_asset_modify(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        limit = float(self.env['ir.config_parameter'].sudo().get_param('activos_fijos.limit'))
        for r in self:
            time_consumed = len(r.depreciation_move_ids.filtered(lambda x: x.state == 'posted'))
            val_min = sorted(r.depreciation_move_ids.filtered(lambda x: x.state == 'posted'), key = lambda y: y.id)
            for rec in val_min:
                value_minimal = rec.historical_depreciation

        if self.no_depreciation_flag == True:
            method_number = 0
        else:
            method_number = abs(self.method_number - time_consumed)

        new_wizard = self.env['asset.modify'].create({
            'asset_id': self.id,
            'method_number': method_number,
            'minium_limit': limit,
            'minium_value': value_minimal * (limit / 100),
            'no_depreciation_flag': self.no_depreciation_flag,
            'work_in_progress': self.work_in_progress,
            'method_period': self.method_period,
            'model_id': self.model_id.id if self.model_id else False,
            'account_inflation_tenure_id': self.account_inflation_tenure_id.id if self.account_inflation_tenure_id else False,
        })
        return {
            'name': _('Modify Asset'),
            'view_mode': 'form',
            'res_model': 'asset.modify',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }

    @api.depends('value_residual', 'salvage_value', 'children_ids.book_value')
    def _compute_book_value(self):
        for record in self:
            record.book_value = record.original_value
            if not record.work_in_progress:
                record.value_residual = record.value_residual - record.salvage_value + sum(
                    record.children_ids.mapped('book_value'))
                record.gross_increase_value = sum(record.children_ids.mapped('original_value'))
            else:
                record.value_residual = record.value_residual - record.salvage_value + sum(
                    record.children_ids.mapped('value_residual'))
                record.gross_increase_value = sum(record.children_ids.mapped('value_residual'))
            record.value_reference = record.value_residual

    # Reescribir funciones para modelos de activos en formulario para activos fijos
    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()
            self.account_analytic_id = model.account_analytic_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id
            self.asset_model_id = model
            self.no_depreciation = model.no_depreciation
            self.account_inflation_tenure_id = model.account_inflation_tenure_id
            self.account_asset_id = model.account_asset_id
            self.work_in_progress = model.work_in_progress

    @api.onchange('no_depreciation')
    def _no_depreciation_control(self):
        if self.no_depreciation:
            self.prorata = False
            self.method = 'bolivian'
            self.method_number = 0
            self.method_period = "1"
            # self.account_depreciation_id = False
            self.account_depreciation_expense_id = False
            self.account_analytic_id = False
            self.analytic_tag_ids = False
            # self.fixed_code = False
            # self.group_suffix = False

    @api.onchange('method')
    def _method_control(self):
        if self.method == 'bolivian':
            self.prorata = False


































