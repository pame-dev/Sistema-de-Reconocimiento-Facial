# database/queries.py
"""
Capa de acceso a datos — equivalente a Stored Procedures en SQLite.
Todas las queries del sistema se centralizan aquí.
Uso: from database.queries import sp_get_usuarios, sp_eliminar_usuario, ...
"""
"prueba para subir a github"
# ════════════════════════════════════════════════════════════════════════════
# USUARIOS — Consultas generales
# ════════════════════════════════════════════════════════════════════════════

def sp_get_usuarios(conn):
    """
    Equivalente a: sp_get_usuarios()
    Retorna todos los usuarios con datos de su rol, fotos y accesos.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.idUsuario,
            u.nombreUsuario,
            u.apellidoPaternoUsuario,
            u.apellidoMaternoUsuario,
            u.matriculaUsuario,
            u.rolUsuario,
            u.telefonoUsuario,
            a.carreraAlumno,
            a.gradoAlumno,
            a.grupoAlumno,
            a.facultadAlumno,
            m.materiaImpartidaMaestro,
            m.gradoImpartidoMaestro,
            p.puestoPersonalEscolar,
            p.areaPersonalEscolar,
            COUNT(DISTINCT b.idBiometria)  AS total_fotos,
            COUNT(DISTINCT ac.idAcceso)    AS total_accesos
        FROM usuarios u
        LEFT JOIN alumnos          a  ON u.idUsuario = a.fkIdUsuario
        LEFT JOIN maestros         m  ON u.idUsuario = m.fkIdUsuario
        LEFT JOIN personal_escolar p  ON u.idUsuario = p.fkIdUsuario
        LEFT JOIN biometria        b  ON u.idUsuario = b.fkIdUsuario
        LEFT JOIN accesos          ac ON u.idUsuario = ac.fkIdUsuario
        GROUP BY u.idUsuario
        ORDER BY u.idUsuario ASC
    """)
    return cursor.fetchall()


def sp_get_usuario_by_id(conn, user_id):
    """
    Equivalente a: sp_get_usuario_by_id(p_id)
    Retorna un usuario específico por su ID.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.idUsuario,
            u.nombreUsuario,
            u.apellidoPaternoUsuario,
            u.apellidoMaternoUsuario,
            u.matriculaUsuario,
            u.rolUsuario,
            u.telefonoUsuario,
            u.correoUsuario,
            u.estadoUsuario
        FROM usuarios u
        WHERE u.idUsuario = ?
    """, (user_id,))
    return cursor.fetchone()


def sp_get_usuarios_by_rol(conn, rol):
    """
    Equivalente a: sp_get_usuarios_by_rol(p_rol)
    Retorna usuarios filtrados por rol.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.idUsuario,
            u.nombreUsuario,
            u.apellidoPaternoUsuario,
            u.apellidoMaternoUsuario,
            u.matriculaUsuario,
            u.rolUsuario,
            u.telefonoUsuario
        FROM usuarios u
        WHERE u.rolUsuario = ?
        ORDER BY u.apellidoPaternoUsuario ASC
    """, (rol,))
    return cursor.fetchall()


# ════════════════════════════════════════════════════════════════════════════
# USUARIOS — Inserción
# ════════════════════════════════════════════════════════════════════════════

def sp_insertar_usuario(conn, datos):
    """
    Equivalente a: sp_insertar_usuario(p_nombre, p_paterno, ...)
    Inserta un usuario base y retorna su ID generado.

    datos = {
        'nombre', 'paterno', 'materno', 'matricula',
        'rol', 'telefono', 'correo'
    }
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usuarios (
            nombreUsuario, apellidoPaternoUsuario, apellidoMaternoUsuario,
            matriculaUsuario, rolUsuario, estadoUsuario,
            telefonoUsuario, correoUsuario
        ) VALUES (?, ?, ?, ?, ?, 'activo', ?, ?)
    """, (
        datos['nombre'],
        datos['paterno'],
        datos.get('materno', ''),
        datos.get('matricula', ''),
        datos['rol'],
        datos.get('telefono', ''),
        datos.get('correo', '')
    ))
    return cursor.lastrowid


def sp_insertar_alumno(conn, user_id, datos):
    """
    Equivalente a: sp_insertar_alumno(p_fk, p_grado, ...)
    datos = { 'grado', 'grupo', 'facultad', 'carrera' }
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alumnos (fkIdUsuario, gradoAlumno, grupoAlumno, facultadAlumno, carreraAlumno)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        datos.get('grado', ''),
        datos.get('grupo', ''),
        datos.get('facultad', ''),
        datos.get('carrera', '')
    ))


def sp_insertar_maestro(conn, user_id, datos):
    """
    Equivalente a: sp_insertar_maestro(p_fk, p_grado, p_materia)
    datos = { 'grado', 'materia' }
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO maestros (fkIdUsuario, gradoImpartidoMaestro, materiaImpartidaMaestro)
        VALUES (?, ?, ?)
    """, (
        user_id,
        datos.get('grado', ''),
        datos.get('materia', '')
    ))


def sp_insertar_personal(conn, user_id, datos):
    """
    Equivalente a: sp_insertar_personal(p_fk, p_puesto, p_area)
    datos = { 'puesto', 'area' }
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO personal_escolar (fkIdUsuario, puestoPersonalEscolar, areaPersonalEscolar)
        VALUES (?, ?, ?)
    """, (
        user_id,
        datos.get('puesto', ''),
        datos.get('area', '')
    ))


def sp_insertar_biometria(conn, user_id, foto_bytes, fecha):
    """
    Equivalente a: sp_insertar_biometria(p_fk, p_foto, p_fecha)
    Inserta una foto biométrica para un usuario.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO biometria (
            fkIdUsuario, encodeBiometria,
            fechaHoraRegistroBiometria, fechaHoraActualizacionBiometria
        ) VALUES (?, ?, ?, ?)
    """, (user_id, foto_bytes, fecha, fecha))


# ════════════════════════════════════════════════════════════════════════════
# USUARIOS — Actualización
# ════════════════════════════════════════════════════════════════════════════

def sp_actualizar_usuario(conn, user_id, datos):
    """
    Equivalente a: sp_actualizar_usuario(p_id, p_nombre, ...)
    datos = { 'nombre', 'paterno', 'materno', 'matricula', 'telefono', 'rol' }
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET nombreUsuario          = ?,
            apellidoPaternoUsuario = ?,
            apellidoMaternoUsuario = ?,
            matriculaUsuario       = ?,
            telefonoUsuario        = ?,
            rolUsuario             = ?,
            fechaHoraActualizacionUsuario = CURRENT_TIMESTAMP
        WHERE idUsuario = ?
    """, (
        datos['nombre'],
        datos['paterno'],
        datos.get('materno', ''),
        datos.get('matricula', ''),
        datos.get('telefono', ''),
        datos['rol'],
        user_id
    ))


def sp_actualizar_alumno(conn, user_id, datos):
    """datos = { 'carrera', 'grado', 'grupo' }"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE alumnos
        SET carreraAlumno = ?, gradoAlumno = ?, grupoAlumno = ?
        WHERE fkIdUsuario = ?
    """, (datos.get('carrera', ''), datos.get('grado', ''), datos.get('grupo', ''), user_id))


def sp_actualizar_maestro(conn, user_id, datos):
    """datos = { 'materia', 'grado' }"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE maestros
        SET materiaImpartidaMaestro = ?, gradoImpartidoMaestro = ?
        WHERE fkIdUsuario = ?
    """, (datos.get('materia', ''), datos.get('grado', ''), user_id))


def sp_actualizar_personal(conn, user_id, datos):
    """datos = { 'puesto', 'area' }"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE personal_escolar
        SET puestoPersonalEscolar = ?, areaPersonalEscolar = ?
        WHERE fkIdUsuario = ?
    """, (datos.get('puesto', ''), datos.get('area', ''), user_id))


# ════════════════════════════════════════════════════════════════════════════
# USUARIOS — Eliminación
# ════════════════════════════════════════════════════════════════════════════

def sp_eliminar_usuario(conn, user_id):
    """
    Equivalente a: sp_eliminar_usuario(p_id)
    Elimina en cascada: biometria, accesos, tabla de rol y usuario.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM biometria        WHERE fkIdUsuario = ?", (user_id,))
    cursor.execute("DELETE FROM accesos          WHERE fkIdUsuario = ?", (user_id,))
    cursor.execute("DELETE FROM alumnos          WHERE fkIdUsuario = ?", (user_id,))
    cursor.execute("DELETE FROM maestros         WHERE fkIdUsuario = ?", (user_id,))
    cursor.execute("DELETE FROM personal_escolar WHERE fkIdUsuario = ?", (user_id,))
    cursor.execute("DELETE FROM usuarios         WHERE idUsuario   = ?", (user_id,))


# ════════════════════════════════════════════════════════════════════════════
# BIOMETRÍA
# ════════════════════════════════════════════════════════════════════════════

def sp_get_fotos_usuario(conn, user_id):
    """
    Equivalente a: sp_get_fotos_usuario(p_id)
    Retorna todas las fotos biométricas de un usuario.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT idBiometria, encodeBiometria, fechaHoraRegistroBiometria
        FROM biometria
        WHERE fkIdUsuario = ?
        ORDER BY fechaHoraRegistroBiometria ASC
    """, (user_id,))
    return cursor.fetchall()


def sp_get_biometria_para_entrenamiento(conn):
    """
    Equivalente a: sp_get_biometria_para_entrenamiento()
    Retorna nombre completo + foto de todos los usuarios con biometría.
    Usado por el módulo de reconocimiento facial.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            u.idUsuario,
            u.nombreUsuario,
            u.apellidoPaternoUsuario,
            u.apellidoMaternoUsuario,
            b.encodeBiometria
        FROM usuarios u
        INNER JOIN biometria b ON u.idUsuario = b.fkIdUsuario
        WHERE b.encodeBiometria IS NOT NULL
        ORDER BY u.idUsuario ASC
    """)
    return cursor.fetchall()


# ════════════════════════════════════════════════════════════════════════════
# ACCESOS
# ════════════════════════════════════════════════════════════════════════════

def sp_registrar_acceso(conn, user_id, estado, confianza, umbral):
    """
    Equivalente a: sp_registrar_acceso(p_fk, p_estado, p_confianza, p_umbral)
    Registra un intento de acceso.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accesos (fkIdUsuario, estado_acceso, confianzaAcceso, umbralConfianzaUsado)
        VALUES (?, ?, ?, ?)
    """, (user_id, estado, confianza, umbral))


def sp_get_historial_accesos(conn, user_id=None, limite=100):
    """
    Equivalente a: sp_get_historial_accesos(p_fk, p_limite)
    Retorna historial de accesos. Si user_id es None, retorna todos.
    """
    cursor = conn.cursor()
    if user_id:
        cursor.execute("""
            SELECT
                ac.idAcceso,
                u.nombreUsuario,
                u.apellidoPaternoUsuario,
                ac.fechaHoraIntentoAcceso,
                ac.estado_acceso,
                ac.confianzaAcceso
            FROM accesos ac
            LEFT JOIN usuarios u ON ac.fkIdUsuario = u.idUsuario
            WHERE ac.fkIdUsuario = ?
            ORDER BY ac.fechaHoraIntentoAcceso DESC
            LIMIT ?
        """, (user_id, limite))
    else:
        cursor.execute("""
            SELECT
                ac.idAcceso,
                u.nombreUsuario,
                u.apellidoPaternoUsuario,
                ac.fechaHoraIntentoAcceso,
                ac.estado_acceso,
                ac.confianzaAcceso
            FROM accesos ac
            LEFT JOIN usuarios u ON ac.fkIdUsuario = u.idUsuario
            ORDER BY ac.fechaHoraIntentoAcceso DESC
            LIMIT ?
        """, (limite,))
    return cursor.fetchall()


def sp_get_estadisticas_accesos(conn):
    """
    Equivalente a: sp_get_estadisticas_accesos()
    Retorna conteo de accesos aceptados y denegados del día.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            estado_acceso,
            COUNT(*) AS total
        FROM accesos
        WHERE DATE(fechaHoraIntentoAcceso) = DATE('now')
        GROUP BY estado_acceso
    """)
    return cursor.fetchall()


# ════════════════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════════════════

def sp_login(conn, matricula):
    """
    Equivalente a: sp_login(p_matricula)
    Busca un usuario por matrícula para autenticación.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT idUsuario, nombreUsuario, rolUsuario, estadoUsuario
        FROM usuarios
        WHERE matriculaUsuario = ?
        AND estadoUsuario = 'activo'
    """, (matricula,))
    return cursor.fetchone()


