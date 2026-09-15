"""
modelos.py  -  Clases de datos de Chocolattor
Reutilizadas directamente de la version de escritorio v5
"""
import math


class InsumoMP:
    def __init__(self, nombre, cantidad, unidad, costo_unit):
        self.nombre     = nombre
        self.cantidad   = cantidad
        self.unidad     = unidad
        self.costo_unit = costo_unit

    def costo_total(self):
        return self.cantidad * self.costo_unit

    def to_dict(self):
        return {"nombre": self.nombre, "cantidad": self.cantidad,
                "unidad": self.unidad, "costo_unit": self.costo_unit}

    @staticmethod
    def from_dict(d):
        return InsumoMP(d["nombre"], d["cantidad"], d["unidad"], d["costo_unit"])


class MateriaPrima:
    TIPOS = ["Licor de cacao", "Manteca de cacao",
             "Cocoa en polvo", "Nibs de cacao", "Otra"]

    def __init__(self, nombre, batch_kg=30.0, rendimiento=75.0):
        self.nombre      = nombre
        self.batch_kg    = batch_kg
        self.rendimiento = rendimiento
        self.insumos     = []

    def costo_total_batch(self):
        return sum(i.costo_total() for i in self.insumos)

    def costo_por_kg(self):
        if self.batch_kg <= 0 or self.rendimiento <= 0:
            return 0.0
        return self.costo_total_batch() / self.batch_kg / (self.rendimiento / 100.0)

    def costo_por_gramo(self):
        return self.costo_por_kg() / 1000.0

    def to_dict(self):
        return {"nombre": self.nombre, "batch_kg": self.batch_kg,
                "rendimiento": self.rendimiento,
                "insumos": [i.to_dict() for i in self.insumos]}

    @staticmethod
    def from_dict(d):
        mp = MateriaPrima(d["nombre"], d.get("batch_kg", 30.0), d.get("rendimiento", 75.0))
        mp.insumos = [InsumoMP.from_dict(x) for x in d.get("insumos", [])]
        return mp


class InsumoGeneral:
    CONV = {"kg": 1000.0, "gr": 1.0, "g": 1.0, "lb": 453.592,
            "oz": 28.3495, "ml": 1.0, "l": 1000.0, "litros": 1000.0, "unidad": 1.0}

    def __init__(self, nombre, cantidad, unidad, costo_total):
        self.nombre      = nombre
        self.cantidad    = cantidad
        self.unidad      = unidad
        self.costo_total = costo_total

    def costo_por_gramo(self):
        factor = self.CONV.get(self.unidad.lower(), 1.0)
        base = self.cantidad * factor
        return self.costo_total / base if base > 0 else 0.0

    def to_dict(self):
        return {"nombre": self.nombre, "cantidad": self.cantidad,
                "unidad": self.unidad, "costo_total": self.costo_total}

    @staticmethod
    def from_dict(d):
        return InsumoGeneral(d["nombre"], d["cantidad"], d["unidad"], d["costo_total"])


class CostoFijo:
    CATEGORIAS = ["General", "Arrendamiento", "Servicios", "Nomina",
                  "Mantenimiento", "Mercadeo", "Depreciacion", "Otro"]

    def __init__(self, nombre, monto, categoria="General"):
        self.nombre    = nombre
        self.monto     = monto
        self.categoria = categoria

    def to_dict(self):
        return {"nombre": self.nombre, "monto": self.monto, "categoria": self.categoria}

    @staticmethod
    def from_dict(d):
        return CostoFijo(d["nombre"], d["monto"], d.get("categoria", "General"))


class OtroGasto:
    def __init__(self, nombre, costo_unit):
        self.nombre     = nombre
        self.costo_unit = costo_unit

    def to_dict(self):
        return {"nombre": self.nombre, "costo_unit": self.costo_unit}

    @staticmethod
    def from_dict(d):
        return OtroGasto(d["nombre"], d["costo_unit"])


class ItemFormulacion:
    def __init__(self, nombre, proporcion_pct):
        self.nombre         = nombre
        self.proporcion_pct = proporcion_pct

    def to_dict(self):
        return {"nombre": self.nombre, "proporcion_pct": self.proporcion_pct}

    @staticmethod
    def from_dict(d):
        return ItemFormulacion(d["nombre"], d["proporcion_pct"])


class Presentacion:
    def __init__(self, nombre, peso_g):
        self.nombre           = nombre
        self.peso_g           = peso_g
        self.formulacion      = []
        self.otros_gastos     = []
        self.cantidad_mensual = 0.0
        self.iva_pct          = 0.0
        self.ganancia_pct     = 0.0

    def cpg(self, nombre_ing, mps, igs):
        n = nombre_ing.strip().lower()
        mp = next((m for m in mps if m.nombre.strip().lower() == n), None)
        if mp: return mp.costo_por_gramo()
        ig = next((i for i in igs if i.nombre.strip().lower() == n), None)
        if ig: return ig.costo_por_gramo()
        return 0.0

    def costo_variable_insumos(self, mps, igs):
        return sum((item.proporcion_pct / 100.0) * self.peso_g *
                   self.cpg(item.nombre, mps, igs)
                   for item in self.formulacion)

    def costo_otros(self):
        return sum(g.costo_unit for g in self.otros_gastos)

    def costo_variable_unit(self, mps, igs):
        return self.costo_variable_insumos(mps, igs) + self.costo_otros()

    def costo_fijo_unit(self, total_cf):
        return total_cf / self.cantidad_mensual if self.cantidad_mensual > 0 else 0.0

    def costo_total_unit(self, mps, igs, total_cf):
        return self.costo_variable_unit(mps, igs) + self.costo_fijo_unit(total_cf)

    def precio_venta(self, mps, igs, total_cf):
        ctu = self.costo_total_unit(mps, igs, total_cf)
        return ctu * (1 + self.iva_pct / 100.0) * (1 + self.ganancia_pct / 100.0)

    def margen_contrib(self, mps, igs, total_cf):
        return (self.precio_venta(mps, igs, total_cf) -
                self.costo_variable_unit(mps, igs))

    def to_dict(self):
        return {
            "nombre": self.nombre, "peso_g": self.peso_g,
            "formulacion":      [x.to_dict() for x in self.formulacion],
            "otros_gastos":     [x.to_dict() for x in self.otros_gastos],
            "cantidad_mensual": self.cantidad_mensual,
            "iva_pct":          self.iva_pct,
            "ganancia_pct":     self.ganancia_pct,
        }

    @staticmethod
    def from_dict(d):
        p = Presentacion(d["nombre"], d["peso_g"])
        p.formulacion      = [ItemFormulacion.from_dict(x) for x in d.get("formulacion", [])]
        p.otros_gastos     = [OtroGasto.from_dict(x)      for x in d.get("otros_gastos", [])]
        p.cantidad_mensual = d.get("cantidad_mensual", 0.0)
        p.iva_pct          = d.get("iva_pct", 0.0)
        p.ganancia_pct     = d.get("ganancia_pct", 0.0)
        return p


def calcular_tir(flujos, max_iter=1000, tol=1e-7):
    t = 0.1
    for _ in range(max_iter):
        vpn  = sum(f / (1+t)**i for i, f in enumerate(flujos))
        dvpn = sum(-i * f / (1+t)**(i+1) for i, f in enumerate(flujos))
        if abs(dvpn) < 1e-14: return None
        nt = t - vpn / dvpn
        if abs(nt - t) < tol: return nt
        t = nt
    return None
