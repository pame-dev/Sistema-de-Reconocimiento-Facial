#!/usr/bin/env python3
"""
Script de diagnóstico para el sistema de reconocimiento facial.
Verifica parámetros críticos y sugiere ajustes.
"""
import os
import sys

# Añadir proyecto root al path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from admin.biometric_system.reconocimiento import ReconocerFacial

def diagnose():
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE RECONOCIMIENTO FACIAL")
    print("=" * 60)
    
    try:
        rec = ReconocerFacial()
        
        print("\n📊 Parámetros Actuales:")
        print(f"  • Tolerancia General: {rec.tolerancia:.2f}")
        print(f"    - Mínimo permitido: {rec._TOLERANCIA_MIN:.2f}")
        print(f"    - Máximo permitido: {rec._TOLERANCIA_MAX:.2f}")
        print(f"  • Margen Soft Recognition: {rec._MARGEN_RECONOCIMIENTO_SUAVE:.2f}")
        print(f"  • Fast-Accept Margin: {rec._fast_accept_margin:.2f}")
        print(f"    → Necesita conf <= {rec.tolerancia - rec._fast_accept_margin:.2f} para aceptar sin votación")
        print(f"  • Margen de Recuperación: {rec._margen_recuperacion:.2f}")
        print(f"  • Frames de votación: {rec._frames_votar}")
        print(f"  • Cooldown post-aceptado: {rec._cooldown_post_aceptado_seg}s")
        print(f"  • Desconocido hold: {rec._desconocido_hold_seg}s")
        
        print("\n🔎 Parámetros Haar Cascade (Detección):")
        print("  • Frontal: scaleFactor=1.1, minNeighbors=6, minSize=(80, 80)")
        print("  • Alt2:    scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)")
        print("  • Perfil:  scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)")
        
        print("\n⚠️  PROBLEMAS IDENTIFICADOS:")
        
        problems = []
        
        # Problema 1: Tolerancia muy alta
        if rec.tolerancia > 85:
            problems.append(
                f"❌ Tolerancia {rec.tolerancia:.1f} es demasiado alta.\n"
                "    LBPH devuelve distancias donde MENOR es MEJOR.\n"
                "    Valores > 85 rechazan casi todas las caras.\n"
                "    → Reduce a 45-65 para Raspberry, 40-50 para PC."
            )
        
        # Problema 2: Fast-accept margin muy alto
        if rec._fast_accept_margin > 6:
            problems.append(
                f"❌ Fast-accept margin ({rec._fast_accept_margin:.1f}) es muy alto.\n"
                "    Requiere distancia <= {:.1f} para aceptar sin votación.\n"
                "    → Reduce a 4-6 para ser más permisivo.".format(
                    rec.tolerancia - rec._fast_accept_margin
                )
            )
        
        # Problema 3: Haar minNeighbors muy restrictivo
        problems.append(
            "❌ Parámetros Haar Cascade frontales son restrictivos:\n"
            "    minNeighbors=6 es alto (valores típicos: 3-5).\n"
            "    → Reduce minNeighbors a 4-5 para detectar más caras."
        )
        
        # Problema 4: Margen soft muy bajo
        if rec._MARGEN_RECONOCIMIENTO_SUAVE < 15:
            problems.append(
                f"❌ Margen soft ({rec._MARGEN_RECONOCIMIENTO_SUAVE:.1f}) muy bajo.\n"
                "    Permite hasta tol+margen = {:.1f}, muy restrictivo.\n"
                "    → Incrementa a 15-25 para mayor flexibilidad.".format(
                    rec.tolerancia + rec._MARGEN_RECONOCIMIENTO_SUAVE
                )
            )
        
        if problems:
            for i, p in enumerate(problems, 1):
                print(f"\n{i}. {p}")
        else:
            print("\n✅ Parámetros normales")
        
        print("\n" + "=" * 60)
        print("💡 RECOMENDACIONES:")
        print("=" * 60)
        print("\n1️⃣  Si NO TE DETECTA (cara roja como 'Desconocido'):")
        print("    ➜ Aumenta tolerancia a 55-65 (más permisivo)")
        print("    ➜ Reduce minNeighbors Haar a 4-5")
        print("    ➜ Aumenta margen soft a 20")
        
        print("\n2️⃣  Si RECHAZA FÁCIL (aunque te detecta):")
        print("    ➜ Aumenta tolerancia a 60-75")
        print("    ➜ Reduce fast-accept-margin a 4")
        print("    ➜ Aumenta margen recuperación a 12-15")
        
        print("\n3️⃣  Para RASPBERRY PI (más interferencia luz/ruido):")
        print("    ➜ Tolerancia: 65-75")
        print("    ➜ Margen soft: 20-25")
        print("    ➜ Fast-accept: 5-6")
        
        print("\n4️⃣  Para PC/Escritorio (control de luz mejor):")
        print("    ➜ Tolerancia: 45-55")
        print("    ➜ Margen soft: 12-18")
        print("    ➜ Fast-accept: 6-8")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
