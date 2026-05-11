from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ciudadanos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ciudadano",
            name="cod_pro",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Codigo del Propietario en dbControl.Propietarios (tramites_db).",
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="ciudadano",
            name="cntr_cod",
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text="CntrCod del contribuyente en MuniJLByR.CONTRIBUYENTES. Null si no es contribuyente.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="ciudadano",
            name="es_propietario",
            field=models.BooleanField(
                default=False,
                help_text="Tiene predios vigentes en el año actual. Habilita BustaCard y pagos.",
            ),
        ),
        migrations.AddField(
            model_name="ciudadano",
            name="fecha_ultima_sync",
            field=models.DateTimeField(
                blank=True,
                help_text="Ultima vez que se sincronizaron datos desde Propietarios/Contribuyentes.",
                null=True,
            ),
        ),
    ]
