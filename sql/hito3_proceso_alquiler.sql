-- =====================================================================
-- Hito 3 - Proceso de alquiler (cabecera - detalle)
-- Base: alquiler_autos_y_camionetas (MySQL / MariaDB)
--
-- Este script deja la base igual que las migraciones de Django:
--   miprimerapp/migrations/0005_proceso_alquiler.py
--   usuarios/migrations/0004_permisos_proceso_alquiler.py
-- Si usás `python manage.py migrate` NO hace falta ejecutarlo:
-- sirve como documentación o para actualizar la base a mano.
-- =====================================================================
USE alquiler_autos_y_camionetas;

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 1) CONTRATO_ALQUILER pasa a ser la CABECERA del proceso
-- ---------------------------------------------------------------------
ALTER TABLE `contrato_alquiler`
  ADD COLUMN `NUMERO_CONTRATO`       varchar(20)   NULL UNIQUE AFTER `ID_CONTRATO`,
  ADD COLUMN `FECHA_CONTRATO`        datetime(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6) AFTER `NUMERO_CONTRATO`,
  ADD COLUMN `CANTIDAD_DIAS`         int unsigned  NOT NULL DEFAULT 1 AFTER `FECHA_FIN`,
  ADD COLUMN `SUBTOTAL`              decimal(12,2) NOT NULL DEFAULT 0 AFTER `CANTIDAD_DIAS`,
  ADD COLUMN `PORCENTAJE_DESCUENTO`  decimal(5,2)  NOT NULL DEFAULT 0 AFTER `SUBTOTAL`,
  ADD COLUMN `IMPORTE_DESCUENTO`     decimal(12,2) NOT NULL DEFAULT 0 AFTER `PORCENTAJE_DESCUENTO`,
  ADD COLUMN `IMPORTE_IVA`           decimal(12,2) NOT NULL DEFAULT 0 AFTER `IMPORTE_DESCUENTO`,
  ADD COLUMN `FECHA_FINALIZACION`    datetime(6)   NULL,
  ADD COLUMN `FECHA_ANULACION`       datetime(6)   NULL,
  ADD COLUMN `MOTIVO_ANULACION`      varchar(255)  NULL,
  ADD COLUMN `ID_EMPLEADO_ANULACION` int(11)       NULL,
  MODIFY COLUMN `MONTO_TOTAL`        decimal(12,2) NOT NULL DEFAULT 0,
  MODIFY COLUMN `ESTADO`             varchar(15)   NOT NULL DEFAULT 'CONFIRMADO',
  MODIFY COLUMN `ID_RESERVA`         int(11)       NULL,   -- el alquiler puede hacerse sin reserva previa
  ADD CONSTRAINT `contrato_alquiler_ID_EMPLEADO_ANULACION_fk_empleados`
      FOREIGN KEY (`ID_EMPLEADO_ANULACION`) REFERENCES `empleados` (`ID_EMPLEADO`);

-- ---------------------------------------------------------------------
-- 2) DETALLE_CONTRATO: un renglón por vehículo alquilado
-- ---------------------------------------------------------------------
CREATE TABLE `detalle_contrato` (
  `ID_DETALLE`    int(11)       NOT NULL AUTO_INCREMENT,
  `ID_CONTRATO`   int(11)       NOT NULL,
  `ID_VEHICULO`   int(11)       NOT NULL,
  `TARIFA_DIARIA` decimal(10,2) NOT NULL,
  `CANTIDAD_DIAS` int unsigned  NOT NULL,
  `SUBTOTAL`      decimal(12,2) NOT NULL,
  PRIMARY KEY (`ID_DETALLE`),
  UNIQUE KEY `uq_detalle_contrato_vehiculo` (`ID_CONTRATO`, `ID_VEHICULO`),
  KEY `detalle_contrato_ID_VEHICULO_fk` (`ID_VEHICULO`),
  CONSTRAINT `detalle_contrato_ID_CONTRATO_fk` FOREIGN KEY (`ID_CONTRATO`) REFERENCES `contrato_alquiler` (`ID_CONTRATO`),
  CONSTRAINT `detalle_contrato_ID_VEHICULO_fk` FOREIGN KEY (`ID_VEHICULO`) REFERENCES `vehiculo` (`ID_VEHICULO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 3) Pasar los contratos que ya existían al detalle y quitar ID_VEHICULO
-- ---------------------------------------------------------------------
UPDATE `contrato_alquiler`
   SET `CANTIDAD_DIAS`   = GREATEST(DATEDIFF(`FECHA_FIN`, `FECHA_INICIO`), 1),
       `SUBTOTAL`        = `MONTO_TOTAL`,
       `NUMERO_CONTRATO` = CONCAT('A-', LPAD(`ID_CONTRATO`, 8, '0')),
       `ESTADO`          = IF(`ESTADO` IN ('CONFIRMADO', 'FINALIZADO', 'ANULADO'), `ESTADO`, 'CONFIRMADO');

INSERT INTO `detalle_contrato` (`ID_CONTRATO`, `ID_VEHICULO`, `TARIFA_DIARIA`, `CANTIDAD_DIAS`, `SUBTOTAL`)
SELECT c.`ID_CONTRATO`, c.`ID_VEHICULO`, cat.`TARIFA`, c.`CANTIDAD_DIAS`, c.`MONTO_TOTAL`
  FROM `contrato_alquiler` c
  JOIN `vehiculo` v             ON v.`ID_VEHICULO`  = c.`ID_VEHICULO`
  JOIN `categoria_vehiculo` cat ON cat.`ID_CATEGORIA` = v.`ID_CATEGORIA`;

ALTER TABLE `contrato_alquiler`
  DROP FOREIGN KEY `contrato_alquiler_ID_VEHICULO_c90376dd_fk_vehiculo_ID_VEHICULO`,
  DROP COLUMN `ID_VEHICULO`;

-- ---------------------------------------------------------------------
-- 4) Permisos del proceso y asignación a perfiles
--    El perfil Empleado registra, consulta, finaliza e imprime, pero NO anula.
-- ---------------------------------------------------------------------
INSERT IGNORE INTO `permiso` (`NOMBRE_PERMISO`, `DESCRIPCION`) VALUES
  ('clientes.gestionar',     'Alta, modificación y baja de clientes'),
  ('vehiculos.gestionar',    'Alta, modificación y baja de vehículos y categorías'),
  ('alquileres.registrar',   'Registrar un alquiler'),
  ('alquileres.consultar',   'Consultar alquileres y ver su detalle'),
  ('alquileres.finalizar',   'Finalizar un alquiler (devolución de vehículos)'),
  ('alquileres.anular',      'Anular un alquiler'),
  ('alquileres.comprobante', 'Emitir el comprobante de un alquiler');

INSERT IGNORE INTO `perfil_permiso` (`ID_PERFIL`, `ID_PERMISO`)
SELECT pf.`ID_PERFIL`, pm.`ID_PERMISO`
  FROM `perfil` pf
  JOIN `permiso` pm
 WHERE pf.`NOMBRE_PERFIL` = 'Administrador'
   AND pm.`NOMBRE_PERMISO` IN ('clientes.gestionar', 'vehiculos.gestionar', 'alquileres.registrar',
                               'alquileres.consultar', 'alquileres.finalizar', 'alquileres.anular',
                               'alquileres.comprobante');

INSERT IGNORE INTO `perfil_permiso` (`ID_PERFIL`, `ID_PERMISO`)
SELECT pf.`ID_PERFIL`, pm.`ID_PERMISO`
  FROM `perfil` pf
  JOIN `permiso` pm
 WHERE pf.`NOMBRE_PERFIL` = 'Empleado'
   AND pm.`NOMBRE_PERMISO` IN ('clientes.gestionar', 'alquileres.registrar', 'alquileres.consultar',
                               'alquileres.finalizar', 'alquileres.comprobante');

UPDATE `perfil` SET `DESCRIPCION` = 'Consulta empleados; registra y consulta alquileres (no puede anular)'
 WHERE `NOMBRE_PERFIL` = 'Empleado';

COMMIT;

-- ---------------------------------------------------------------------
-- 5) Datos de ejemplo: categorías con tarifas reales de referencia
--    (Perfil Rent a Car) y un vehículo por categoría (patentes inventadas).
--    Equivale a: python manage.py cargar_datos_ejemplo
-- ---------------------------------------------------------------------
INSERT INTO categoria_vehiculo (NOMBRE_CATEGORIA, TAMANIO, TARIFA, PRECIO, EQUIPAMIENTO, ESTADO, FECHA_ALTA) VALUES
  ('Económico',     'Chico',    50000.00,  350000.00, 'Aire acondicionado, ABS, airbags, km ilimitado', 'ACTIVO', CURDATE()),
  ('Sedán',         'Mediano',  68700.00,  480900.00, 'Aire acondicionado, ABS, airbags, baúl, km ilimitado', 'ACTIVO', CURDATE()),
  ('Camioneta 4x4', 'Grande',  170000.00, 1190000.00, '4x4, caja automática, dirección hidráulica, aire acondicionado, ABS, airbags, km ilimitado', 'ACTIVO', CURDATE())
ON DUPLICATE KEY UPDATE TAMANIO = VALUES(TAMANIO), TARIFA = VALUES(TARIFA), PRECIO = VALUES(PRECIO), EQUIPAMIENTO = VALUES(EQUIPAMIENTO);

INSERT INTO vehiculo (PATENTE, MARCA, MODELO, ESTADO_OPERATIVO, ID_CATEGORIA, FECHA_ALTA, ESTADO)
SELECT v.PATENTE, v.MARCA, v.MODELO, 'DISPONIBLE', c.ID_CATEGORIA, CURDATE(), 'ACTIVO'
  FROM (SELECT 'AE123FG' AS PATENTE, 'Chevrolet' AS MARCA, 'Onix 1.4 manual' AS MODELO, 'Económico' AS CATEGORIA
        UNION ALL SELECT 'AF456HJ', 'Renault', 'Logan 1.6 manual', 'Sedán'
        UNION ALL SELECT 'AG789KL', 'Toyota', 'Hilux 2.8 automática 4x4', 'Camioneta 4x4') v
  JOIN categoria_vehiculo c ON c.NOMBRE_CATEGORIA = v.CATEGORIA
ON DUPLICATE KEY UPDATE MARCA = VALUES(MARCA), MODELO = VALUES(MODELO), ID_CATEGORIA = VALUES(ID_CATEGORIA);
