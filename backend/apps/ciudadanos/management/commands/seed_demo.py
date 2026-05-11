"""Genera datos de ejemplo para desarrollo: ciudadano demo, deudas, tramites, tarjeta."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalogos.models import Contacto, LugarInteres, Noticia
from apps.ciudadanos.models import Ciudadano
from apps.deudas.models import Deuda, EstadoDeuda, TipoDeuda
from apps.tarjetas.models import Beneficio, TarjetaCiudadana
from apps.tramites.models import AreaMunicipal, TipoTramite


class Command(BaseCommand):
    help = "Crea datos iniciales para pruebas (ciudadano demo, catalogos, deudas, etc.)"

    def handle(self, *args, **options):
        self._crear_ciudadano_demo()
        self._crear_areas_y_tramites()
        self._crear_deudas_demo()
        self._crear_beneficios()
        self._crear_tarjeta_demo()
        self._crear_catalogos()
        self.stdout.write(self.style.SUCCESS("Datos demo cargados correctamente."))

    def _crear_ciudadano_demo(self):
        self.ciudadano, creado = Ciudadano.objects.get_or_create(
            dni="12345678",
            defaults={
                "nombres": "Juan Carlos",
                "apellido_paterno": "Perez",
                "apellido_materno": "Condori",
                "email": "demo@munibustamante.gob.pe",
                "celular": "987654321",
                "direccion": "Av. Dolores 123 - JLBR",
                "verificado": True,
            },
        )
        if creado:
            self.ciudadano.set_password("demo1234")
            self.ciudadano.save()
            self.stdout.write("  - Ciudadano demo creado (DNI 12345678 / demo1234)")

        # superusuario para admin
        if not Ciudadano.objects.filter(is_superuser=True).exists():
            Ciudadano.objects.create_superuser(
                dni="00000000",
                password="admin1234",
                nombres="Admin",
                apellido_paterno="Municipal",
            )
            self.stdout.write("  - Superusuario admin creado (DNI 00000000 / admin1234)")

    def _crear_areas_y_tramites(self):
        areas = {
            "Gerencia de Desarrollo Urbano": "GDU",
            "Gerencia de Administracion Tributaria": "GAT",
            "Gerencia de Servicios Comunales": "GSC",
            "Gerencia de Desarrollo Social": "GDS",
        }
        self.areas = {}
        for nombre, siglas in areas.items():
            self.areas[nombre], _ = AreaMunicipal.objects.get_or_create(
                nombre=nombre, defaults={"siglas": siglas}
            )

        tramites = [
            {
                "codigo": "LIC-001",
                "nombre": "Licencia de funcionamiento",
                "descripcion": "Tramite para apertura de establecimientos comerciales.",
                "area": "Gerencia de Desarrollo Urbano",
                "requisitos": [
                    "Formulario unico de tramite",
                    "Copia de DNI",
                    "Plano de distribucion",
                    "Certificado ITSE",
                ],
                "costo": Decimal("120.00"),
                "dias_habiles": 15,
            },
            {
                "codigo": "PRE-001",
                "nombre": "Declaracion jurada de autoavaluo",
                "descripcion": "Presentacion anual de declaracion de predios.",
                "area": "Gerencia de Administracion Tributaria",
                "requisitos": ["DNI", "Documento del predio"],
                "costo": Decimal("0.00"),
                "dias_habiles": 5,
            },
            {
                "codigo": "CON-001",
                "nombre": "Constancia de no adeudo",
                "descripcion": "Emision de constancia de no tener deudas tributarias.",
                "area": "Gerencia de Administracion Tributaria",
                "requisitos": ["DNI", "Recibo de pago tasa"],
                "costo": Decimal("15.00"),
                "dias_habiles": 3,
            },
            {
                "codigo": "SER-001",
                "nombre": "Solicitud de limpieza publica",
                "descripcion": "Reporte o solicitud de recojo de residuos especiales.",
                "area": "Gerencia de Servicios Comunales",
                "requisitos": ["Descripcion del lugar"],
                "costo": Decimal("0.00"),
                "dias_habiles": 7,
            },
        ]
        for t in tramites:
            TipoTramite.objects.get_or_create(
                codigo=t["codigo"],
                defaults={
                    "nombre": t["nombre"],
                    "descripcion": t["descripcion"],
                    "area": self.areas[t["area"]],
                    "requisitos": "\n".join(t["requisitos"]),
                    "costo": t["costo"],
                    "dias_habiles": t["dias_habiles"],
                },
            )
        self.stdout.write("  - Areas y tipos de tramite cargados")

    def _crear_deudas_demo(self):
        hoy = date.today()
        deudas = [
            (TipoDeuda.PREDIAL, "Impuesto predial 2024 - cuota 1", 2024, "Trimestre 1", Decimal("180.50"), EstadoDeuda.VENCIDA),
            (TipoDeuda.PREDIAL, "Impuesto predial 2024 - cuota 2", 2024, "Trimestre 2", Decimal("180.50"), EstadoDeuda.PENDIENTE),
            (TipoDeuda.ARBITRIOS, "Arbitrios 2024 - limpieza publica", 2024, "Anual", Decimal("210.00"), EstadoDeuda.PENDIENTE),
            (TipoDeuda.ARBITRIOS, "Arbitrios 2024 - parques y jardines", 2024, "Anual", Decimal("96.00"), EstadoDeuda.PENDIENTE),
            (TipoDeuda.PREDIAL, "Impuesto predial 2023", 2023, "Anual", Decimal("540.00"), EstadoDeuda.PAGADA),
        ]
        for i, (tipo, concepto, anio, periodo, monto, estado) in enumerate(deudas, start=1):
            Deuda.objects.get_or_create(
                codigo_referencia=f"DEM-{self.ciudadano.dni}-{i:03d}",
                defaults={
                    "ciudadano": self.ciudadano,
                    "tipo": tipo,
                    "concepto": concepto,
                    "anio": anio,
                    "periodo": periodo,
                    "monto": monto,
                    "interes": Decimal("0.00") if estado != EstadoDeuda.VENCIDA else Decimal("12.40"),
                    "fecha_emision": date(anio, 1, 15),
                    "fecha_vencimiento": hoy - timedelta(days=30) if estado == EstadoDeuda.VENCIDA else hoy + timedelta(days=60),
                    "estado": estado,
                },
            )
        self.stdout.write("  - Deudas demo cargadas")

    def _crear_beneficios(self):
        beneficios = [
            ("Ingreso libre a la Biblioteca Municipal", "Acceso gratuito los fines de semana.", "CULTURA", "Biblioteca Municipal JLBR"),
            ("Uso de losa deportiva", "Reserva de losa por una hora sin costo.", "DEPORTE", "Complejo Deportivo Municipal"),
            ("Talleres culturales", "Descuento total en talleres municipales.", "CULTURA", "Casa de la Cultura"),
            ("Chequeo medico gratuito", "Campanas de salud mensuales.", "SALUD", "Posta municipal"),
            ("Parques y zonas de recreacion", "Ingreso preferencial con tarjeta ciudadana.", "RECREO", "Parques JLBR"),
        ]
        for nombre, desc, categoria, lugar in beneficios:
            Beneficio.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": desc,
                    "categoria": categoria,
                    "lugar": lugar,
                    "gratuito": True,
                    "horario": "Lun a Sab de 08:00 a 18:00",
                },
            )
        self.stdout.write("  - Beneficios cargados")

    def _crear_tarjeta_demo(self):
        if not hasattr(self.ciudadano, "tarjeta"):
            TarjetaCiudadana.objects.create(
                ciudadano=self.ciudadano,
                fecha_vencimiento=timezone.now().date().replace(year=timezone.now().year + 1),
            )
            self.stdout.write("  - Tarjeta ciudadana demo emitida")

    def _crear_catalogos(self):
        noticias = [
            ("Mejoramiento de parques en Bustamante y Rivero", "La municipalidad ejecutara obras de mejoramiento en 10 parques del distrito.", True),
            ("Campana de limpieza vecinal", "Convocamos a vecinos a jornada de limpieza este sabado.", False),
            ("Nuevos talleres gratuitos 2026", "Inscripciones abiertas para talleres de verano.", True),
        ]
        for titulo, resumen, destacada in noticias:
            Noticia.objects.get_or_create(
                titulo=titulo,
                defaults={
                    "resumen": resumen,
                    "contenido": resumen,
                    "destacada": destacada,
                },
            )

        lugares = [
            ("Parque Lambramani", "PARQUE", "Av. Lambramani s/n"),
            ("Biblioteca Municipal JLBR", "BIBLIOTECA", "Av. Dolores 200"),
            ("Complejo Deportivo Municipal", "COMPLEJO", "Urb. La Negrita"),
            ("Serenazgo JLBR", "SERENAZGO", "Av. EE.UU. 300"),
        ]
        for nombre, tipo, direccion in lugares:
            LugarInteres.objects.get_or_create(
                nombre=nombre,
                defaults={"tipo": tipo, "direccion": direccion},
            )

        contactos = [
            ("Central municipal", "054-000000", "central@munibustamante.gob.pe", 1),
            ("Serenazgo", "054-111111", "serenazgo@munibustamante.gob.pe", 2),
            ("Atencion al ciudadano", "054-222222", "atencion@munibustamante.gob.pe", 3),
        ]
        for area, telefono, email, orden in contactos:
            Contacto.objects.get_or_create(
                area=area,
                defaults={
                    "telefono": telefono,
                    "email": email,
                    "orden": orden,
                    "horario": "Lun a Vie 08:00 - 16:30",
                },
            )
        self.stdout.write("  - Catalogos cargados")
