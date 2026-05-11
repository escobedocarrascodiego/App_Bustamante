"""
Modelos de solo lectura contra la BD `tramites_db` (dbControl).

Todos los modelos tienen `managed = False`: Django nunca hara migraciones
contra esta base. Las ForeignKey a tablas no incluidas (Urbanizaciones,
Usuarios, Oficinas) se declaran como CharField/IntegerField para no tener
que definir esos modelos ahora. Se pueden promover a FK cuando los
necesitemos en alguna vista.
"""
from django.db import models


class Documentos(models.Model):
    cod_doc = models.CharField(primary_key=True, max_length=8)
    nom_doc = models.CharField(max_length=70)
    sig_doc = models.CharField(max_length=25, blank=True, null=True)
    cod_ger = models.CharField(max_length=8, blank=True, null=True)
    cod_sub = models.CharField(max_length=8, blank=True, null=True)
    cod_ofi = models.CharField(max_length=8, blank=True, null=True)
    est_doc = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Documentos"

    def __str__(self):
        return f"{self.cod_doc} - {self.nom_doc}"


class DocumentosExternos(models.Model):
    """
    Catalogo de documentos del portal externo. Distinto de `Documentos`
    (TUPA interno). `IngresosExternos.cod_docext` tiene FK contra esta
    tabla, asi que el INSERT debe usar un cod_docext que exista aqui
    (ej. DOC00847 para tramites).
    """

    cod_docext = models.CharField(primary_key=True, max_length=8)
    nom_docext = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "DocumentosExternos"

    def __str__(self):
        return f"{self.cod_docext} - {self.nom_docext}"


class Oficinas(models.Model):
    cod_ofi = models.CharField(primary_key=True, max_length=8)
    nom_ofi = models.CharField(max_length=100)
    cod_ger = models.CharField(max_length=8, blank=True, null=True)
    cod_sub = models.CharField(max_length=8, blank=True, null=True)
    cod_jef = models.CharField(max_length=8, blank=True, null=True)
    sig_ofi = models.CharField(max_length=25, blank=True, null=True)
    est_ger = models.BooleanField(blank=True, null=True)
    ofi_est = models.BooleanField(blank=True, null=True)
    est_sub = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Oficinas"

    def __str__(self):
        return f"{self.cod_ofi} - {self.nom_ofi}"


class Solicitudes(models.Model):
    cod_sol = models.CharField(primary_key=True, max_length=6)
    nom_sol = models.CharField(max_length=200)
    pla_sol = models.DecimalField(max_digits=5, decimal_places=0)
    pag_sol = models.DecimalField(max_digits=19, decimal_places=4)
    pag_uit = models.DecimalField(max_digits=19, decimal_places=4)
    aut = models.BooleanField()
    pos = models.BooleanField()
    neg = models.BooleanField()
    ini_tra = models.CharField(max_length=100)
    aut_apr = models.CharField(max_length=100)
    rec_sol = models.CharField(max_length=100, blank=True, null=True)
    ape_sol = models.CharField(max_length=100, blank=True, null=True)
    nor_leg = models.CharField(max_length=200, blank=True, null=True)
    cod_ofi = models.CharField(max_length=8)
    est_tup = models.BooleanField()
    cod_tup = models.FloatField()
    est_otr = models.BooleanField()
    est_int = models.BooleanField()
    tup_otr = models.BooleanField()
    tod_hab = models.BooleanField()
    ord_mun = models.CharField(max_length=100, blank=True, null=True)
    fec_ord = models.DateTimeField(blank=True, null=True)
    est_act = models.BooleanField(blank=True, null=True)
    cod_initra = models.CharField(max_length=8, blank=True, null=True)
    cod_autapr = models.CharField(max_length=8, blank=True, null=True)
    cod_recsol = models.CharField(max_length=8, blank=True, null=True)
    cod_apesol = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Solicitudes"

    def __str__(self):
        return f"{self.cod_sol} - {self.nom_sol}"


class SolicitudesExternas(models.Model):
    """
    Catalogo de solicitudes que el ciudadano puede generar desde el portal
    externo (no es la misma que la tabla `Solicitudes` del TUPA interno).
    """

    cod_solext = models.CharField(primary_key=True, max_length=8)
    nom_solext = models.CharField(max_length=200)
    est_tupext = models.BooleanField(blank=True, null=True)
    est_otrext = models.BooleanField(blank=True, null=True)
    tup_otrext = models.BooleanField(blank=True, null=True)
    est_actext = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "SolicitudesExternas"

    def __str__(self):
        return f"{self.cod_solext} - {self.nom_solext}"


class Propietarios(models.Model):
    cod_pro = models.CharField(primary_key=True, max_length=10)
    nom_pro = models.CharField(max_length=200, blank=True, null=True)
    dni_pro = models.CharField(max_length=15, blank=True, null=True)
    dom_pro = models.CharField(max_length=10, blank=True, null=True)
    mnz_pro = models.CharField(max_length=8, blank=True, null=True)
    lot_pro = models.CharField(max_length=8, blank=True, null=True)
    cal_pro = models.CharField(max_length=150, blank=True, null=True)
    cod_dis = models.CharField(max_length=8, blank=True, null=True)
    fec_per = models.DateTimeField(blank=True, null=True)
    cod_pass = models.IntegerField(blank=True, null=True)
    est_pro = models.BooleanField(blank=True, null=True)
    est_con = models.BooleanField(blank=True, null=True)
    est_tra = models.BooleanField(blank=True, null=True)
    nom_rep = models.CharField(max_length=200, blank=True, null=True)
    tel_pro = models.CharField(max_length=50, blank=True, null=True)
    pat_pro = models.CharField(max_length=60, blank=True, null=True)
    mat_pro = models.CharField(max_length=60, blank=True, null=True)
    pnom_pro = models.CharField(max_length=80, blank=True, null=True)
    sex_pro = models.CharField(max_length=10, blank=True, null=True)
    email_pro = models.CharField(max_length=80, blank=True, null=True)
    per_pro = models.CharField(max_length=10, blank=True, null=True)
    est_com = models.BooleanField(blank=True, null=True)
    cod_siap = models.IntegerField(blank=True, null=True)
    ruc_pro = models.CharField(max_length=11, blank=True, null=True)
    dni_rep = models.CharField(max_length=8, blank=True, null=True)
    dir_rep = models.CharField(max_length=150, blank=True, null=True)
    id_usuaext = models.IntegerField(blank=True, null=True)
    id_aspnetusers = models.CharField(max_length=128, blank=True, null=True)
    pais_usuaext = models.CharField(max_length=8, blank=True, null=True)
    dep_usuaext = models.CharField(max_length=8, blank=True, null=True)
    prov_usuaext = models.CharField(max_length=8, blank=True, null=True)
    obs_usuaext = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Propietarios"

    def __str__(self):
        return f"{self.cod_pro} - {self.nom_pro or ''}"

    @property
    def nombre_completo(self) -> str:
        if self.nom_pro:
            return self.nom_pro
        partes = [self.pnom_pro, self.pat_pro, self.mat_pro]
        return " ".join(p for p in partes if p)


class Ingresos(models.Model):
    cod_ing = models.AutoField(primary_key=True)
    fec_ing = models.DateTimeField()
    cod_doc = models.ForeignKey(Documentos, models.DO_NOTHING, db_column="cod_doc")
    num_doc = models.CharField(max_length=20)
    cod_sol = models.ForeignKey(Solicitudes, models.DO_NOTHING, db_column="cod_sol")
    cod_pro = models.ForeignKey(Propietarios, models.DO_NOTHING, db_column="cod_pro")
    cod_pass = models.IntegerField()
    fec_mes = models.DateTimeField()
    cod_ofi = models.CharField(max_length=8)
    ofi_tra = models.CharField(max_length=8)
    des_sol = models.CharField(max_length=500, blank=True, null=True)
    est_sol = models.BooleanField(blank=True, null=True)
    est_obs = models.BooleanField(blank=True, null=True)
    fec_ven = models.DateTimeField(blank=True, null=True)
    obs_req = models.CharField(max_length=200, blank=True, null=True)
    est_ofi = models.BooleanField(blank=True, null=True)
    obs_ofi = models.CharField(max_length=200, blank=True, null=True)
    est_der = models.BooleanField(blank=True, null=True)
    fec_obs = models.DateTimeField(blank=True, null=True)
    usua_obs = models.CharField(max_length=4, blank=True, null=True)
    per_enc = models.CharField(max_length=4, blank=True, null=True)
    est_eli = models.BooleanField(blank=True, null=True)
    cod_ing2 = models.CharField(max_length=50, blank=True, null=True)
    cod_pass2 = models.CharField(max_length=50, blank=True, null=True)
    est_adj = models.BooleanField(blank=True, null=True)
    cod_gering = models.CharField(max_length=8, blank=True, null=True)
    cod_subing = models.CharField(max_length=8, blank=True, null=True)
    cod_ingext = models.IntegerField(blank=True, null=True)
    ubi_ingpdf = models.CharField(max_length=30, blank=True, null=True)
    fec_ingpdf = models.DateTimeField(blank=True, null=True)
    cod_passpdf = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Ingresos"


class IngresosExternos(models.Model):
    """
    Registro de tramites generados desde el portal externo (ahora tambien
    desde el app movil). Insert via raw SQL para bypassear el router
    read-only de `tramites_db`.
    """

    cod_ingext = models.AutoField(primary_key=True)
    fec_ingext = models.DateTimeField()
    cod_docext = models.CharField(max_length=8)
    num_docext = models.CharField(max_length=20, blank=True, null=True)
    cod_solext = models.CharField(max_length=8)
    des_solext = models.CharField(max_length=500, blank=True, null=True)
    ofi_traext = models.CharField(max_length=8, blank=True, null=True)
    ofi_recext = models.CharField(max_length=8, blank=True, null=True)
    # SQL Server columna real: DATE (sin hora). Si se declara DateTimeField,
    # el driver mssql-django explota con `'datetime.date' object has no
    # attribute 'utcoffset'` al intentar adaptarlo a aware datetime.
    fec_venext = models.DateField(blank=True, null=True)
    doc_adjext = models.BinaryField(blank=True, null=True)
    id_usuaext = models.IntegerField(blank=True, null=True)
    id_aspnetusers = models.CharField(max_length=128, blank=True, null=True)
    cod_expext = models.IntegerField(blank=True, null=True)
    num_expext = models.CharField(max_length=20, blank=True, null=True)
    nom_adjext = models.CharField(max_length=200, blank=True, null=True)
    est_actext = models.BooleanField(blank=True, null=True)
    obs_actext = models.CharField(max_length=200, blank=True, null=True)
    fec_actext = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "IngresosExternos"


class Proveidos(models.Model):
    cod_prov = models.AutoField(primary_key=True)
    cod_ing = models.ForeignKey(Ingresos, models.DO_NOTHING, db_column="cod_ing")
    fec_prov = models.DateTimeField()
    cod_doc = models.CharField(max_length=8)
    num_prov = models.CharField(max_length=80)
    cod_pro = models.CharField(max_length=10)
    cod_ofi = models.CharField(max_length=8)
    acc_tom = models.CharField(max_length=500, blank=True, null=True)
    cod_pass = models.IntegerField()
    ofi_tra = models.CharField(max_length=8)
    est_sol = models.BooleanField(blank=True, null=True)
    cod_gerprov = models.CharField(max_length=8, blank=True, null=True)
    cod_subprov = models.CharField(max_length=8, blank=True, null=True)
    cod_lic = models.CharField(max_length=10, blank=True, null=True)
    fec_rec = models.DateTimeField(blank=True, null=True)
    cod_usua = models.IntegerField(blank=True, null=True)
    est_rec = models.BooleanField(blank=True, null=True)
    est_email = models.BooleanField(blank=True, null=True)
    fec_email = models.DateTimeField(blank=True, null=True)
    pdf_email = models.CharField(max_length=200, blank=True, null=True)
    cod_passemail = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Proveidos"
