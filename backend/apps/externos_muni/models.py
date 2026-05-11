"""
Modelos de solo lectura contra la BD `muni_db` (MuniJLByR - SIAP).

Solo declaramos CONTRIBUYENTES como ORM. Las consultas complejas de deuda
(CTACTE, IMPPREANU, LICENCIAANU, etc.) se ejecutan como SQL crudo via
`connections['muni_db'].cursor()` en la capa de servicios para no duplicar
esquemas gigantes ni arriesgar mapeos incorrectos.
"""
from django.db import models


class Contribuyentes(models.Model):
    cntrcod = models.IntegerField(db_column="CntrCod", primary_key=True)
    cntrtipoper = models.SmallIntegerField(db_column="CntrTipoPer")
    cntrapepat = models.CharField(db_column="CntrApePat", max_length=20)
    cntrapemat = models.CharField(db_column="CntrApeMat", max_length=20)
    cntrprinom = models.CharField(db_column="CntrPriNom", max_length=20)
    cntrsegnon = models.CharField(db_column="CntrSegNon", max_length=40)
    cntrnom = models.CharField(db_column="CntrNom", max_length=80)
    cntridenticod = models.SmallIntegerField(db_column="CntrIdentiCod")
    cntrnumdoc = models.CharField(db_column="CntrNumDoc", max_length=15)
    cntrdirec = models.CharField(db_column="CntrDirec", max_length=80)
    cntrreplegnom = models.CharField(db_column="CntrRepLegNom", max_length=60)
    cntrreplegiden = models.SmallIntegerField(db_column="CntrRepLegIden")
    cntrreplegnum = models.CharField(db_column="CntrRepLegNum", max_length=15)
    cntrreplegdir = models.CharField(db_column="CntrRepLegDir", max_length=80)
    cntrfecnac = models.DateTimeField(db_column="CntrFecNac", blank=True, null=True)
    cntrtelnum = models.CharField(db_column="CntrTelNum", max_length=20)
    cntrcelnum = models.CharField(db_column="CntrCelNum", max_length=20)
    cntrmail = models.CharField(db_column="CntrMail", max_length=60)
    estcivcod = models.SmallIntegerField(db_column="EstCivCod")
    cntrcodant = models.CharField(db_column="CntrCodAnt", max_length=6)
    cntrconide = models.SmallIntegerField(db_column="CntrConIde", blank=True, null=True)
    cntrconnum = models.CharField(db_column="CntrConNum", max_length=15, blank=True, null=True)
    cntrconapepat = models.CharField(db_column="CntrConApePat", max_length=20, blank=True, null=True)
    cntrconapemat = models.CharField(db_column="CntrConApeMat", max_length=20, blank=True, null=True)
    cntrconprinom = models.CharField(db_column="CntrConPriNom", max_length=20, blank=True, null=True)
    cntrconsegnom = models.CharField(db_column="CntrConSegNom", max_length=40, blank=True, null=True)
    cntrconnom = models.CharField(db_column="CntrConNom", max_length=80, blank=True, null=True)
    cntrconfecnac = models.DateTimeField(db_column="CntrConFecNac", blank=True, null=True)
    cntrconmail = models.CharField(db_column="CntrConMail", max_length=60, blank=True, null=True)
    cntrcodant1 = models.IntegerField(db_column="CntrCodAnt1", blank=True, null=True)
    cntrflgpobreza = models.SmallIntegerField(db_column="CntrFlgPobreza")
    cntrcrefec = models.DateTimeField(db_column="CntrCreFec")
    cntrcreusu = models.IntegerField(db_column="CntrCreUsu")
    cntrmodfec = models.DateTimeField(db_column="CntrModFec")
    cntrmodusu = models.IntegerField(db_column="CntrModUsu")
    cntranu = models.CharField(db_column="CntrAnu", max_length=1)
    cntrruc = models.DecimalField(db_column="CntrRuc", max_digits=11, decimal_places=0)
    cntrzonacod = models.IntegerField(db_column="CntrZonaCod")
    cntrmza = models.CharField(db_column="CntrMza", max_length=5)
    cntrlote = models.CharField(db_column="CntrLote", max_length=5)
    cntrsec = models.CharField(db_column="CntrSec", max_length=5)
    cntrvia = models.IntegerField(db_column="CntrVia")
    cntrnume = models.CharField(db_column="CntrNume", max_length=5)
    cntrdirec2 = models.CharField(db_column="CntrDirec2", max_length=80)
    cntrdirecflg = models.SmallIntegerField(db_column="CntrDirecFlg")
    depcod = models.SmallIntegerField(db_column="DepCod", blank=True, null=True)
    procod = models.SmallIntegerField(db_column="ProCod", blank=True, null=True)
    discod = models.SmallIntegerField(db_column="DisCod", blank=True, null=True)
    paiscod = models.IntegerField(db_column="PaisCod", blank=True, null=True)
    cntrdireclar = models.CharField(db_column="CntrDirecLar", max_length=160)
    cntrflgwrk1 = models.IntegerField(db_column="CntrFlgWrk1")

    class Meta:
        managed = False
        db_table = "CONTRIBUYENTES"

    def __str__(self):
        return f"{self.cntrcod} - {self.cntrnom}"
