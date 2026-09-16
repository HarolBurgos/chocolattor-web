"""
modelos.py  -  Clases de datos de Chocolattor
Reutilizadas directamente de la version de escritorio v5
"""
import math

class MateriaPrima:
    def __init__(self, nombre, costo, unidad="kg", rendimiento=100.0):
        self.nombre = nombre
        self.costo = float(costo)
        self.unidad = unidad
        self.rendimiento = float(rendimiento)

    def costo_real_unitario(self):
        """Calcula el costo real unitario considerando la pérdida por rendimiento."""
        if self.rendimiento > 0:
            return self.costo / (self.rendimiento / 100.0)
        return self.costo

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "costo": self.costo,
            "unidad": self.unidad,
            "rendimiento": self.rendimiento
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            nombre=data.get("nombre", ""),
            costo=data.get("costo", 0.0),
            unidad=data.get("unidad", "kg"),
            rendimiento=data.get("rendimiento", 100.0)
        )


class InsumoGeneral:
    def __init__(self, nombre, costo, unidad="unidad"):
        self.nombre = nombre
        self.costo = float(costo)
        self.unidad = unidad

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "costo": self.costo,
            "unidad": self.unidad
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            nombre=data.get("nombre", ""),
            costo=data.get("costo", 0.0),
            unidad=data.get("unidad", "unidad")
        )


class CostoFijo:
    def __init__(self, nombre, monto):
        self.nombre = nombre
        self.monto = float(monto)

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "monto": self.monto
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            nombre=data.get("nombre", ""),
            monto=data.get("monto", 0.0)
        )


class OtroGasto:
    def __init__(self, nombre, monto):
        self.nombre = nombre
        self.monto = float(monto)

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "monto": self.monto
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            nombre=data.get("nombre", ""),
            monto=data.get("monto", 0.0)
        )


class ItemFormulacion:
    def __init__(self, materia_prima: MateriaPrima, porcentaje: float):
        self.materia_prima = materia_prima
        self.porcentaje = float(porcentaje)

    def calcular_costo_item(self, peso_total_g: float):
        """Calcula el costo del ingrediente según el peso total del producto en gramos."""
        peso_ingrediente_kg = (peso_total_g * (self.porcentaje / 100.0)) / 1000.0
        return peso_ingrediente_kg * self.materia_prima.costo_real_unitario()

    def to_dict(self):
        return {
            "materia_prima_nombre": self.materia_prima.nombre,
            "porcentaje": self.porcentaje
        }


class InsumoMP:
    def __init__(self, insumo: InsumoGeneral, cantidad: float = 1.0):
        self.insumo = insumo
        self.cantidad = float(cantidad)

    def calcular_costo_insumo(self):
        return self.insumo.costo * self.cantidad

    def to_dict(self):
        return {
            "insumo_nombre": self.insumo.nombre,
            "cantidad": self.cantidad
        }


class Presentacion:
    def __init__(self, nombre: str, peso_g: float, items_formulacion: list, insumos: list = None, margen_deseado: float = 30.0):
        self.nombre = nombre
        self.peso_g = float(peso_g)
        self.items_formulacion = items_formulacion  # Lista de ItemFormulacion
        self.insumos = insumos if insumos is not None else []  # Lista de InsumoMP
        self.margen_deseado = float(margen_deseado)

    def calcular_cvu(self):
        """Calcula el Costo Variable Unitario (CVU)."""
        costo_mp = sum(item.calcular_costo_item(self.peso_g) for item in self.items_formulacion)
        costo_ins = sum(ins.calcular_costo_insumo() for ins in self.insumos)
        return costo_mp + costo_ins

    def precio_sugerido(self):
        """Calcula el precio de venta sugerido basado en el margen deseado."""
        cvu = self.calcular_cvu()
        if self.margen_deseado < 100:
            return cvu / (1.0 - (self.margen_deseado / 100.0))
        return cvu * (1.0 + (self.margen_deseado / 100.0))

    def to_dict(self):
        return {
            "nombre": self.nombre,
            "peso_g": self.peso_g,
            "margen_deseado": self.margen_deseado,
            "items_formulacion": [item.to_dict() for item in self.items_formulacion],
            "insumos": [ins.to_dict() for ins in self.insumos]
        }

    @classmethod
    def from_dict(cls, data, lista_mp, lista_ig):
        items = []
        for it in data.get("items_formulacion", []):
            mp = next((x for x in lista_mp if x.nombre == it.get("materia_prima_nombre")), None)
            if mp:
                items.append(ItemFormulacion(mp, it.get("porcentaje", 0.0)))

        insumos = []
        for ins in data.get("insumos", []):
            ig = next((x for x in lista_ig if x.nombre == ins.get("insumo_nombre")), None)
            if ig:
                insumos.append(InsumoMP(ig, ins.get("cantidad", 1.0)))

        return cls(
            nombre=data.get("nombre", ""),
            peso_g=data.get("peso_g", 0.0),
            items_formulacion=items,
            insumos=insumos,
            margen_deseado=data.get("margen_deseado", 30.0)
        )


def calcular_tir(flujos, tol=1e-6, max_iter=1000):
    """Calcula la Tasa Interna de Retorno (TIR) por método de Newton-Raphson."""
    guest = 0.1
    for _ in range(max_iter):
        f_val = sum(f / ((1 + guest) ** i) for i, f in enumerate(flujos))
        f_der = sum(-i * f / ((1 + guest) ** (i + 1)) for i, f in enumerate(flujos))
        if abs(f_der) < 1e-12:
            break
        new_guest = guest - f_val / f_der
        if abs(new_guest - guest) < tol:
            return new_guest
        guest = new_guest
    return None

