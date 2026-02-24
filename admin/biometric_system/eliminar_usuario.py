# eliminar_usuario.py
import sqlite3

def eliminar_usuario():
    """Elimina un usuario y todos sus registros relacionados"""
    
    conn = sqlite3.connect('database/sistema_biometrico.db')
    cursor = conn.cursor()
    
    print("="*50)
    print("🗑️  ELIMINAR USUARIO DEL SISTEMA")
    print("="*50)
    
    # Mostrar usuarios existentes
    cursor.execute("""
        SELECT u.idUsuario, u.nombreUsuario, u.apellidoPaternoUsuario, 
               u.rolUsuario, COUNT(b.idBiometria) as fotos
        FROM usuarios u
        LEFT JOIN biometria b ON u.idUsuario = b.fkIdUsuario
        GROUP BY u.idUsuario
    """)
    
    usuarios = cursor.fetchall()
    
    if not usuarios:
        print("❌ No hay usuarios registrados")
        conn.close()
        return
    
    print("\n📋 Usuarios disponibles:")
    for user in usuarios:
        print(f"   ID: {user[0]} | {user[1]} {user[2]} | Rol: {user[3]} | Fotos: {user[4]}")
    
    try:
        user_id = int(input("\n👉 ID del usuario a eliminar: "))
    except ValueError:
        print("❌ ID inválido")
        conn.close()
        return
    
    # Verificar que existe
    cursor.execute("SELECT nombreUsuario, apellidoPaternoUsuario FROM usuarios WHERE idUsuario = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        print("❌ Usuario no encontrado")
        conn.close()
        return
    
    nombre_completo = f"{user[0]} {user[1]}"
    
    print(f"\n⚠️  ¿Estás SEGURO de eliminar a {nombre_completo}?")
    print("   Se eliminarán TODOS sus datos:")
    print("   - Información personal")
    print("   - Fotos biométricas")
    print("   - Historial de accesos")
    
    confirmacion = input("\n   Escribe 'ELIMINAR' para confirmar: ")
    
    if confirmacion != 'ELIMINAR':
        print("❌ Eliminación cancelada")
        conn.close()
        return
    
    # 1. Eliminar de tabla alumnos (si aplica)
    cursor.execute("DELETE FROM alumnos WHERE fkIdUsuario = ?", (user_id,))
    print(f"   ✅ Alumnos: {cursor.rowcount} registros")
    
    # 2. Eliminar de tabla maestros (si aplica)
    cursor.execute("DELETE FROM maestros WHERE fkIdUsuario = ?", (user_id,))
    print(f"   ✅ Maestros: {cursor.rowcount} registros")
    
    # 3. Eliminar de tabla personal_escolar (si aplica)
    cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))
    print(f"   ✅ Personal escolar: {cursor.rowcount} registros")
    
    # 4. Eliminar fotos de biometria
    cursor.execute("DELETE FROM biometria WHERE fkIdUsuario = ?", (user_id,))
    fotos_eliminadas = cursor.rowcount
    print(f"   ✅ Biometria: {fotos_eliminadas} fotos eliminadas")
    
    # 5. Eliminar historial de accesos
    cursor.execute("DELETE FROM accesos WHERE fkIdUsuario = ?", (user_id,))
    print(f"   ✅ Accesos: {cursor.rowcount} registros")
    
    # 6. Finalmente, eliminar el usuario
    cursor.execute("DELETE FROM usuarios WHERE idUsuario = ?", (user_id,))
    print(f"   ✅ Usuario eliminado")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print(f"✅ Usuario {nombre_completo} eliminado correctamente")
    print(f"   {fotos_eliminadas} fotos eliminadas")
    print("="*50)

if __name__ == "__main__":
    eliminar_usuario()