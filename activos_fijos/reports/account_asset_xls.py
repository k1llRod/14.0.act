from odoo import models

class AccountAssetXLS(models.AbstractModel):
    _name = 'report.account_asset.report_account_asset_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Reporte xls"

    def generate_xlsx_report(self, workbook, data, lines):
        format1 = workbook.add_format({'font_size':11, 'align': 'vcenter','bold': True})
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format3 = workbook.add_format({'num_format': 'dd/mm/yy','font_size': 10, 'align': 'vcenter'})
        sheet = workbook.add_worksheet("account asset")
        sheet.write(0, 0, 'Nombre del activo', format1)
        sheet.write(0, 1, 'Código', format1)
        sheet.write(0, 2, 'Valor original', format1)
        sheet.write(0, 3, 'Fecha de adquisición', format1)
        sheet.write(0, 4, 'Grupo contable', format1)
        sheet.write(0, 5, 'UFV inicial', format1)
        sheet.write(0, 6, 'Fecha inicial', format1)
        sheet.write(0, 7, 'Fecha final', format1)
        sheet.write(0, 8, 'UFV final', format1)
        sheet.write(0, 9, 'Incremento por actualización', format1)
        sheet.write(0, 10, 'Valor actualizado', format1)
        sheet.write(0, 11, 'Depreciación acumulada inicial', format1)
        sheet.write(0, 12, 'AITB', format1)
        sheet.write(0, 13, 'Depreciación', format1)
        sheet.write(0, 14, 'Depreciación acumulada actualizada', format1)
        sheet.write(0, 15, 'Valor neto', format1)


        c = 1
        for r in lines:
            sheet.write(c, 0,r.name, format2)
            sheet.write(c, 1, r.codigo_activo, format2)
            sheet.write(c, 2, r.original_value, format2)
            sheet.write(c, 3, r.acquisition_date, format3)
            sheet.write(c, 4, r.model_id.name, format2)
            for rec in r.depreciation_move_ids.sorted(key = lambda m: m.id).filtered(lambda m: m.state == 'posted'):
                sheet.write(c, 5, rec.initial_ufv, format2)
                sheet.write(c, 6, rec.initial_date, format3)
                sheet.write(c, 7, rec.date_ufv, format3)
                sheet.write(c, 8, rec.value_ufv, format2)
                sheet.write(c, 9, rec.updated_increment, format2)
                sheet.write(c, 10, rec.updated_item, format2)
                sheet.write(c, 11, rec.depreciation_initial, format2)
                sheet.write(c, 12, rec.aitb, format2)
                sheet.write(c, 13, rec.asset_depreciated_value, format2)
                sheet.write(c, 14, rec.year_acumulated_depreciation_updated, format2)
                sheet.write(c, 15, rec.net_worth_item, format2)

            c = c+1

