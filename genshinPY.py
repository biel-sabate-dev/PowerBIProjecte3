import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict
import json
import re

def fetch_and_analyze():
    url = "https://genshin-builds.com/es/banners/characters"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
    }
    
    print(f"Obteniendo datos de {url}...")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error al acceder a la página: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    character_appearances = defaultdict(list)
    banners_data = []

    # Estrategia mejorada: Buscar cualquier texto que tenga formato de fecha (ej. 2024-06-05)
    date_pattern = re.compile(r'20[2-3]\d-[0-1]\d-[0-3]\d')
    date_elements = soup.find_all(string=date_pattern)
    
    print(f"Se encontraron {len(date_elements)} posibles fechas en la web.")

    for element in date_elements:
        # Extraemos solo la parte de la fecha
        match = date_pattern.search(element.text)
        if not match:
            continue
            
        date_str = match.group()
        try:
            banner_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Subimos en el árbol HTML (hasta 5 niveles) buscando el contenedor que tenga las imágenes de los personajes
            parent = element.parent
            characters = []
            
            for _ in range(5):
                if parent is None:
                    break
                
                # Buscamos todas las imágenes dentro de este contenedor
                imgs = parent.find_all('img')
                for img in imgs:
                    alt_text = img.get('alt', '').strip()
                    # Filtramos logos e imágenes sin nombre
                    if alt_text and alt_text not in characters and "logo" not in alt_text.lower():
                        characters.append(alt_text)
                
                # Si ya encontramos personajes, no necesitamos subir más en el HTML
                if characters:
                    break
                    
                parent = parent.parent
            
            if characters:
                banners_data.append({
                    'date': date_str,
                    'characters': characters
                })
                
                for char in characters:
                    character_appearances[char].append(banner_date)

        except ValueError:
            continue

    if not banners_data:
        print("\n¡ATENCIÓN! No se pudo extraer ningún banner.")
        print("Posible causa: La web carga sus datos con JavaScript o la estructura ha cambiado drásticamente.")
        # Guardamos un log del HTML para poder inspeccionarlo
        with open('debug_html.txt', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        return

    print(f"¡Éxito! Se procesaron {len(banners_data)} banners.")

    # Analizar patrones de rerun
    predictions = []
    
    for char, dates in character_appearances.items():
        # Ordenamos las fechas de más reciente a más antigua
        dates.sort(reverse=True) 
        if len(dates) > 1:
            diffs = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
            avg_diff = sum(diffs) / len(diffs)
            
            last_appearance = dates[0]
            next_predicted_date = last_appearance + timedelta(days=avg_diff)
            
            # Solo guardamos si la predicción es futura
            if next_predicted_date > datetime.now():
                predictions.append({
                    'character': char,
                    'last_appearance': last_appearance.strftime('%Y-%m-%d'),
                    'avg_days_between_reruns': round(avg_diff),
                    'predicted_next_rerun': next_predicted_date.strftime('%Y-%m-%d')
                })

    # Ordenar predicciones
    predictions.sort(key=lambda x: x['predicted_next_rerun'])
    
    # Guardar archivos
    with open('banners_history.json', 'w', encoding='utf-8') as f:
        json.dump(banners_data, f, indent=4, ensure_ascii=False)
        
    with open('rerun_predictions.json', 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=4, ensure_ascii=False)
        
    print("Análisis completado y archivos JSON generados con éxito.")

if __name__ == '__main__':
    fetch_and_analyze()
