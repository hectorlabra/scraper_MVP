#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script para el procesamiento de grandes conjuntos de datos.

Este script prueba el nuevo método deduplicate_large_dataset que implementa
procesamiento en paralelo y por lotes para conjuntos de datos extensos.
"""

import os
import sys
import pandas as pd
import logging
import time
import random
from pathlib import Path
import numpy as np

# Añadir el directorio raíz del proyecto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from processing.data_processor import DeduplicationProcessor

def generate_synthetic_data(num_records=100000, duplicate_ratio=0.3, similarity_ratio=0.2):
    """
    Genera un conjunto de datos sintético grande con duplicados exactos y similares.
    
    Args:
        num_records: Número total de registros a generar
        duplicate_ratio: Proporción de duplicados exactos
        similarity_ratio: Proporción de registros similares (no exactos)
        
    Returns:
        DataFrame con datos sintéticos
    """
    logging.info(f"Generando {num_records} registros sintéticos...")
    
    # Definir nombres de negocios base
    business_name_templates = [
        "Restaurante {}", "Café {}", "Hotel {}", "Tienda {}", "Farmacia {}", 
        "Consultorio {}", "Estudio {}", "Taller {}", "Gimnasio {}", "Clínica {}"
    ]
    
    # Definir adjetivos para crear variaciones
    adjectives = [
        "Central", "Del Centro", "Nuevo", "Viejo", "Moderno", "Tradicional", 
        "Familiar", "Exclusivo", "Premium", "Económico", "Elegante", "Rústico",
        "Internacional", "Local", "Regional", "Artesanal", "Gourmet", "Ejecutivo"
    ]
    
    # Definir ubicaciones
    locations = [
        "Ciudad de México", "CDMX", "Ciudad de Mexico", "Guadalajara", "Monterrey", 
        "Puebla", "Querétaro", "Mérida", "Tijuana", "Cancún", "Ciudad Juárez",
        "Santiago", "Santiago de Chile", "Buenos Aires", "Córdoba", "Rosario", 
        "Lima", "Bogotá", "Medellín", "Cali", "Barranquilla", "Caracas", "Maracaibo"
    ]
    
    # Prefijos y sufijos para introducir variaciones similares
    prefixes = ["", "El ", "La ", "Los ", "Las ", "Mi ", "Nuevo ", "Gran ", "Super "]
    suffixes = ["", " Plus", " Express", " & Asociados", " S.A.", " Ltda.", " Inc.", " Company"]
    
    # Generamos los datos base únicos
    unique_records = int(num_records * (1 - duplicate_ratio - similarity_ratio))
    
    # Crear datos base
    data = []
    for i in range(unique_records):
        business_type = random.choice(business_name_templates)
        adjective = random.choice(adjectives)
        name = business_type.format(adjective)
        
        record = {
            'business_name': name,
            'phone': f"+{random.randint(1, 59)}-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            'email': f"info@{name.lower().replace(' ', '')}.com".replace('í', 'i').replace('á', 'a').replace('é', 'e').replace('ó', 'o').replace('ú', 'u'),
            'location': random.choice(locations),
            'website': f"www.{name.lower().replace(' ', '')}.com".replace('í', 'i').replace('á', 'a').replace('é', 'e').replace('ó', 'o').replace('ú', 'u'),
            'description': f"{name} es un negocio líder en su sector.",
            'employees': random.randint(5, 500),
            'founding_year': random.randint(1950, 2023)
        }
        data.append(record)
    
    # Agregar duplicados exactos
    exact_duplicates = int(num_records * duplicate_ratio)
    for _ in range(exact_duplicates):
        # Seleccionar un registro aleatorio para duplicar
        original = random.choice(data[:unique_records])
        duplicate = original.copy()
        
        # Posiblemente modificar algún campo no usado para comparación (employees, founding_year)
        if random.random() > 0.5:
            duplicate['employees'] = random.randint(5, 500)
        if random.random() > 0.5:
            duplicate['founding_year'] = random.randint(1950, 2023)
            
        data.append(duplicate)
    
    # Agregar registros similares (no exactos)
    similar_records = int(num_records * similarity_ratio)
    for _ in range(similar_records):
        # Seleccionar un registro aleatorio para crear una variante similar
        original = random.choice(data[:unique_records])
        similar = original.copy()
        
        # Modificar el nombre para que sea similar pero no idéntico
        name_parts = original['business_name'].split()
        if len(name_parts) > 1:
            # Agregar o quitar prefijo/sufijo
            if random.random() > 0.5:
                prefix = random.choice(prefixes)
                similar['business_name'] = prefix + original['business_name']
            else:
                suffix = random.choice(suffixes)
                similar['business_name'] = original['business_name'] + suffix
                
            # Posible cambio de mayúsculas/minúsculas
            if random.random() > 0.7:
                similar['business_name'] = similar['business_name'].upper()
            elif random.random() > 0.5:
                similar['business_name'] = similar['business_name'].title()
        
        # Posiblemente modificar ubicación ligeramente
        if random.random() > 0.7:
            # Mantener ubicación similar (ej. "Ciudad de México" vs "CDMX")
            location = original['location']
            if location == "Ciudad de México":
                similar['location'] = "CDMX"
            elif location == "CDMX":
                similar['location'] = "Ciudad de Mexico"
            elif location == "Santiago":
                similar['location'] = "Santiago de Chile"
            elif location == "Buenos Aires":
                similar['location'] = "CABA"
                
        # Generar emails y sitios web relacionados al nombre modificado
        if random.random() > 0.5:
            clean_name = similar['business_name'].lower().replace(' ', '')
            clean_name = clean_name.replace('í', 'i').replace('á', 'a').replace('é', 'e').replace('ó', 'o').replace('ú', 'u')
            similar['email'] = f"contacto@{clean_name}.com"
            similar['website'] = f"www.{clean_name}.com"
            
        data.append(similar)
    
    # Convertir a DataFrame y mezclar aleatoriamente
    df = pd.DataFrame(data)
    df = df.sample(frac=1).reset_index(drop=True)
    
    logging.info(f"Dataset generado: {len(df)} registros ({unique_records} únicos, {exact_duplicates} duplicados exactos, {similar_records} similares)")
    return df

def test_deduplication_methods(df, match_fields, threshold=80):
    """
    Compara el rendimiento de diferentes métodos de deduplicación.
    
    Args:
        df: DataFrame con datos a deduplicar
        match_fields: Campos a usar para comparación
        threshold: Umbral de similitud para fuzzy matching
    """
    # Copia de seguridad para usar el mismo dataset en todos los tests
    df_copy = df.copy()
    
    # Test 1: Método estándar de deduplicación exacta
    logging.info("Iniciando test de deduplicación exacta estándar...")
    processor = DeduplicationProcessor(df_copy)
    start_time = time.time()
    result_exact = processor.deduplicate_exact(match_fields)
    exact_time = time.time() - start_time
    exact_record_count = len(result_exact)
    logging.info(f"Deduplicación exacta completada en {exact_time:.2f} segundos. Registros restantes: {exact_record_count}")
    
    # Test 2: Método estándar de deduplicación fuzzy
    logging.info("Iniciando test de deduplicación fuzzy estándar...")
    processor = DeduplicationProcessor(df_copy)
    start_time = time.time()
    result_fuzzy = processor.deduplicate_fuzzy(column=match_fields[0], threshold=threshold)
    fuzzy_time = time.time() - start_time
    fuzzy_record_count = len(result_fuzzy)
    logging.info(f"Deduplicación fuzzy completada en {fuzzy_time:.2f} segundos. Registros restantes: {fuzzy_record_count}")
    
    # Test 3: Método optimizado para grandes datasets (secuencial)
    logging.info("Iniciando test de deduplicación optimizada (modo secuencial)...")
    processor = DeduplicationProcessor(df_copy)
    start_time = time.time()
    result_large_seq = processor.deduplicate_large_dataset(match_fields=match_fields, threshold=threshold, use_parallel=False)
    large_seq_time = time.time() - start_time
    large_seq_record_count = len(result_large_seq)
    logging.info(f"Deduplicación optimizada (secuencial) completada en {large_seq_time:.2f} segundos. Registros restantes: {large_seq_record_count}")
    
    # Test 4: Método optimizado para grandes datasets (paralelo)
    logging.info("Iniciando test de deduplicación optimizada (modo paralelo)...")
    processor = DeduplicationProcessor(df_copy)
    start_time = time.time()
    result_large_parallel = processor.deduplicate_large_dataset(match_fields=match_fields, threshold=threshold, use_parallel=True)
    large_parallel_time = time.time() - start_time
    large_parallel_record_count = len(result_large_parallel)
    logging.info(f"Deduplicación optimizada (paralelo) completada en {large_parallel_time:.2f} segundos. Registros restantes: {large_parallel_record_count}")
    
    # Resumen de resultados
    logging.info("\nRESUMEN DE PRUEBAS DE RENDIMIENTO:")
    logging.info(f"Dataset original: {len(df_copy)} registros")
    logging.info(f"1. Deduplicación exacta: {exact_record_count} registros, {exact_time:.2f} segundos")
    logging.info(f"2. Deduplicación fuzzy: {fuzzy_record_count} registros, {fuzzy_time:.2f} segundos")
    logging.info(f"3. Deduplicación optimizada (secuencial): {large_seq_record_count} registros, {large_seq_time:.2f} segundos")
    logging.info(f"4. Deduplicación optimizada (paralelo): {large_parallel_record_count} registros, {large_parallel_time:.2f} segundos")
    
    # Calcular mejoras de rendimiento
    fuzzy_vs_optimized = (fuzzy_time / large_parallel_time) if large_parallel_time > 0 else 0
    seq_vs_parallel = (large_seq_time / large_parallel_time) if large_parallel_time > 0 else 0
    
    logging.info(f"Mejora de rendimiento (fuzzy vs optimizado paralelo): {fuzzy_vs_optimized:.2f}x")
    logging.info(f"Mejora de rendimiento (secuencial vs paralelo): {seq_vs_parallel:.2f}x")
    
    # Verificar consistencia de resultados
    logging.info("\nVERIFICACIÓN DE CONSISTENCIA:")
    exact_vs_fuzzy_diff = abs(exact_record_count - fuzzy_record_count)
    fuzzy_vs_large_diff = abs(fuzzy_record_count - large_parallel_record_count)
    
    logging.info(f"Diferencia entre exacto y fuzzy: {exact_vs_fuzzy_diff} registros")
    logging.info(f"Diferencia entre fuzzy y optimizado: {fuzzy_vs_large_diff} registros")
    
    # Verificar consistencia entre secuencial y paralelo
    seq_vs_parallel_diff = abs(large_seq_record_count - large_parallel_record_count)
    logging.info(f"Diferencia entre optimizado secuencial y paralelo: {seq_vs_parallel_diff} registros")
    
    return {
        'exact': {'time': exact_time, 'records': exact_record_count},
        'fuzzy': {'time': fuzzy_time, 'records': fuzzy_record_count},
        'large_seq': {'time': large_seq_time, 'records': large_seq_record_count},
        'large_parallel': {'time': large_parallel_time, 'records': large_parallel_record_count},
        'fuzzy_vs_optimized': fuzzy_vs_optimized,
        'seq_vs_parallel': seq_vs_parallel
    }

def test_with_increasing_sizes():
    """
    Prueba el rendimiento con tamaños crecientes de conjunto de datos.
    """
    sizes = [1000, 5000, 10000, 50000, 100000]
    results = {}
    
    for size in sizes:
        logging.info(f"\n{'='*50}")
        logging.info(f"PRUEBA CON TAMAÑO DE DATASET: {size} REGISTROS")
        logging.info(f"{'='*50}")
        
        df = generate_synthetic_data(num_records=size)
        match_fields = ['business_name', 'location', 'phone']
        
        result = test_deduplication_methods(df, match_fields)
        results[size] = result
    
    # Análisis de escalabilidad
    logging.info("\n\nANÁLISIS DE ESCALABILIDAD:")
    
    # Imprimir tabla de tiempos
    logging.info(f"{'Tamaño':<10} | {'Exacto (s)':<12} | {'Fuzzy (s)':<12} | {'Optimizado (s)':<12} | {'Mejora':<8}")
    logging.info(f"{'-'*10} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*8}")
    
    for size, result in results.items():
        logging.info(f"{size:<10} | {result['exact']['time']:<12.2f} | {result['fuzzy']['time']:<12.2f} | " +
                     f"{result['large_parallel']['time']:<12.2f} | {result['fuzzy_vs_optimized']:<8.2f}x")

def main():
    """
    Función principal que ejecuta todas las pruebas.
    """
    logging.info("Iniciando pruebas de rendimiento para deduplicación de grandes datasets")
    
    # Crear directorio para los resultados si no existe
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Opción 1: Prueba única con un tamaño grande
    if len(sys.argv) > 1 and sys.argv[1] == '--single':
        size = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
        logging.info(f"Ejecutando prueba única con {size} registros")
        
        df = generate_synthetic_data(num_records=size)
        match_fields = ['business_name', 'location', 'phone']
        
        # Guardar dataset para referencia
        df.to_csv(os.path.join(results_dir, f"synthetic_data_{size}.csv"), index=False)
        
        test_deduplication_methods(df, match_fields)
    
    # Opción 2: Prueba de escalabilidad con tamaños crecientes
    else:
        logging.info("Ejecutando prueba de escalabilidad")
        test_with_increasing_sizes()

if __name__ == "__main__":
    main()
