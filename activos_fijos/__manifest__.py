# -*- coding: utf-8 -*-
{
    'name': "Activos Fijos",

    'summary': """
        Activos Fijos Localización Boliviana""",

    'description': """
        Manejo de activos fijos acorde a normativa nacional boliviana vigente.
        1. Registro de activos singular y por compras.
        2. Método de depreciación en base a cotización moneda UFV (Unidad de fomento a la vivienda)
        3. Eliminación y/o venta de activos fijos.
    """,

    'author': "Versatil SRL - Rodrigo Loza",
    'website': "http://www.versatil.com.bo",

    'category': 'Accounting',
    'version': '14.1',

    'depends': ['base','account_asset', 'report_xlsx', 'web_notify'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'views/cron.xml',
        'views/accounting_group.xml',
        'views/res_currency.xml',
        'views/account_asset.xml',
        # 'views/res_config_settings.xml',
        'views/templates.xml',
        'views/account_asset_log.xml',
        'data/secuencia.xml',
        'data/account_asset.xml',
        'reports/report.xml',
        'wizard/asset_modify.xml',
        'wizard/activate_work.xml',
    ],

}
