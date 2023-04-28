# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class activos_fijos(models.Model):
#     _name = 'activos_fijos.activos_fijos'
#     _description = 'activos_fijos.activos_fijos'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

from odoo import models, fields, api

class grupocontable(models.Model):
    _name = 'activos_fijos.grupocontable'
    _description = 'Grupos contables'

    id_grupo = fields.Char(string='Codigo grupo contable')
    name = fields.Char('Grupo contable',required=True)
    vida_util = fields.Integer('Vida util',required=True)
    coeficiente = fields.Float(string='coefieciente')


class ufv(models.Model):
    _name = 'activos_fijos.ufv'
    _description = 'UFV'

    name = fields.Float('Valor del ufv',required=True)
    fecha_registro = fields.Date('Fecha de registro del UFV', required=True)

class activofijo(models.Model):
    _name = 'activos_fijos.activofijo'
    _description = 'Descripcion del activo'

    #FUNCION FILTRAR POR TIPO UFV
    def _compute_field(self):
        domain = self.env.ref('activos_fijos.ufv1')
        return [('currency_id','=',domain.id)]

    codigo_activo = fields.Char(string='Codigo del activo fijo', required=True)
    grupo_contable_id = fields.Many2one(
        'activos_fijos.grupocontable',
        string='Grupo contable', required=True
    )
    descripcion = fields.Char(string='Descripcion del activo',required=True)

    @api.onchange('costo_adquisicion')
    def compute_field(self):
        self.credito_fiscal = self.costo_adquisicion * 0.13

    costo_adquisicion = fields.Float(string='Monto adquirido', required=True)

    credito_fiscal = fields.Float(string='13% del monto')


    currency_rate = fields.Many2one(
        comodel_name='res.currency.rate',
        string='Fecha UFV',
        domain=_compute_field
    )
    valor=fields.Float('Valor UFV',related='currency_rate.rate')

class tabla_depreciacion(models.Model):
    _name = 'activos_fijos.tabla_depreciacion'
    _description = 'Tabla de historial de depreciacion del activo fijo'

    name = fields.Char(string='Descripcion del activo fijo',required=True)
    fecha_depreciacion = fields.Date(string='Fecha inicio de depreciacion')
    ufv_inicial = fields.Float(string='UFV inicial')
    fecha_final = fields.Date(string='Fecha final')
    ufv_final = fields.Float(string='UFV final')
    depreciacion = fields.Float(string='Calculo de depreciacion')
    depreciacion_acumulada = fields.Float(string='Depreciacion acumulada')
    asiento_contable = fields.Char(string='asiento contable')

    activo_id = fields.Many2one(
        'account.asset',
        'activo'
    )









