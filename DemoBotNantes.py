import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="IA Chatbot Parkings Nantes",
    page_icon="🅿️",
    layout="wide"
)

# Titre et introduction
st.title("🅿️ IA Chatbot - Parkings de Nantes Métropole")
st.markdown("Posez des questions sur la disponibilité des parkings à Nantes. Notre IA vous aidera à trouver les meilleures options.")

# Configuration de l'API Claude
CLAUDE_API_KEY = st.secrets.get("CLAUDE_API_KEY", os.environ.get("CLAUDE_API_KEY", ""))
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Si la clé API n'est pas disponible, afficher un avertissement
if not CLAUDE_API_KEY:
    st.warning("⚠️ Clé API Claude non trouvée. Le chatbot fonctionnera en mode basique.")

# URLs des API pour les parkings de Nantes
PARKING_APIS = {
    "parkings_disponibilites": "https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_parkings-publics-nantes-disponibilites/records?limit=100",
    "parcs_relais_disponibilites": "https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_parcs-relais-nantes-metropole-disponibilites/records?limit=100",
    "parkings_infos": "https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_parkings-publics-nantes/records?limit=100",
    "parcs_relais_infos": "https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_parcs-relais-nantes-metropole/records?limit=100"
}

# Fonction pour récupérer les données depuis une API
def fetch_data(api_url):
    """Interroge une API pour récupérer des données."""
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        else:
            st.error(f"⚠️ Structure de données inattendue pour {api_url}")
            return []
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des données: {str(e)}")
        return []

# Fonction pour récupérer et combiner toutes les données de parking
def fetch_all_parking_data():
    """Récupère les données de toutes les API de parking et les combine."""
    data = {}
    
    with st.spinner("Récupération des données de parking en cours..."):
        for key, url in PARKING_APIS.items():
            data[key] = fetch_data(url)
    
    return data

# Fonction pour préparer les données de parkings pour l'IA
def prepare_parking_data(parking_data):
    """Combine et prépare les données de parking pour l'IA."""
    # Vérifier si nous avons des données
    if not parking_data or not any(parking_data.values()):
        return "Aucune donnée de parking disponible."
    
    # Traiter les données de disponibilité des parkings publics
    parking_dispo = {}
    if parking_data.get("parkings_disponibilites"):
        for item in parking_data["parkings_disponibilites"]:
            if "grp_nom" in item and "grp_disponible" in item:
                parking_dispo[item["grp_nom"]] = {
                    "places_disponibles": item.get("grp_disponible", 0),
                    "places_totales": item.get("grp_exploitation", 0),
                    "statut": item.get("grp_statut", ""),
                    "derniere_mise_a_jour": item.get("grp_horodatage", "")
                }
    
    # Traiter les données de disponibilité des parcs relais
    parcs_relais_dispo = {}
    if parking_data.get("parcs_relais_disponibilites"):
        for item in parking_data["parcs_relais_disponibilites"]:
            if "libelle" in item and "disponible" in item:
                parcs_relais_dispo[item["libelle"]] = {
                    "places_disponibles": item.get("disponible", 0),
                    "places_totales": item.get("capacite", 0),
                    "derniere_mise_a_jour": item.get("lastupdate", "")
                }
    
    # Combiner avec les informations détaillées des parkings
    parkings_complets = []
    
    # Pour les parkings publics
    if parking_data.get("parkings_infos"):
        for item in parking_data["parkings_infos"]:
            nom = item.get("nom", "")
            parking_info = {
                "nom": nom,
                "type": "Parking public",
                "adresse": item.get("adresse", ""),
                "coordonnees": {"lat": item.get("location_lat", ""), "lon": item.get("location_lon", "")},
                "infos": {
                    "tarif_1h": item.get("tarif_1h", ""),
                    "tarif_2h": item.get("tarif_2h", ""),
                    "hauteur_max": item.get("hauteur_max", ""),
                    "nb_pmr": item.get("nb_pmr", ""),
                    "nb_voitures_electriques": item.get("nb_voitures_electriques", ""),
                    "horaires_semaine": item.get("horaires_semaine", ""),
                    "horaires_dimanche": item.get("horaires_dimanche", "")
                }
            }
            
            # Ajouter les données de disponibilité si présentes
            if nom in parking_dispo:
                parking_info["disponibilite"] = parking_dispo[nom]
            
            parkings_complets.append(parking_info)
    
    # Pour les parcs relais
    if parking_data.get("parcs_relais_infos"):
        for item in parking_data["parcs_relais_infos"]:
            nom = item.get("libelle", "")
            parking_info = {
                "nom": nom,
                "type": "Parc relais",
                "adresse": item.get("adresse", ""),
                "coordonnees": {"lat": item.get("geo_point_2d", {}).get("lat", ""), 
                               "lon": item.get("geo_point_2d", {}).get("lon", "")},
                "infos": {
                    "capacite": item.get("capacite", ""),
                    "nb_pmr": item.get("capacite_pmr", ""),
                    "info_complementaires": item.get("info_complementaires", ""),
                    "ligne_tram": item.get("ligne_tram", "")
                }
            }
            
            # Ajouter les données de disponibilité si présentes
            if nom in parcs_relais_dispo:
                parking_info["disponibilite"] = parcs_relais_dispo[nom]
            
            parkings_complets.append(parking_info)
    
    return json.dumps(parkings_complets, ensure_ascii=False, indent=2)

# Fonction pour formater les données de façon lisible
def format_parking_info(parking_info):
    """Formate les informations d'un parking pour l'affichage."""
    if isinstance(parking_info, str):
        try:
            parking_info = json.loads(parking_info)
        except:
            return parking_info
    
    formatted_info = ""
    for parking in parking_info:
        formatted_info += f"### {parking.get('nom', 'Parking sans nom')} ({parking.get('type', '')})\n\n"
        
        if "disponibilite" in parking:
            dispo = parking["disponibilite"]
            formatted_info += f"**Disponibilité**: {dispo.get('places_disponibles', '?')}/{dispo.get('places_totales', '?')} places\n"
            
            if "derniere_mise_a_jour" in dispo:
                try:
                    update_time = dispo["derniere_mise_a_jour"]
                    if isinstance(update_time, str) and "T" in update_time:
                        date_str, time_str = update_time.split("T")
                        time_str = time_str.split("+")[0]
                        formatted_info += f"*Mise à jour: {date_str} à {time_str}*\n"
                except:
                    pass
        
        formatted_info += f"**Adresse**: {parking.get('adresse', 'Non précisée')}\n\n"
        
        if "infos" in parking:
            infos = parking["infos"]
            for key, value in infos.items():
                if value:
                    # Formater les clés pour meilleure lisibilité
                    key_display = key.replace("_", " ").capitalize()
                    formatted_info += f"- **{key_display}**: {value}\n"
        
        formatted_info += "\n---\n\n"
    
    return formatted_info

# Fonction pour interroger Claude API directement avec requests
def ask_claude(user_query, parking_data, conversation_history):
    if not CLAUDE_API_KEY:
        return "Mode IA désactivé. Utilisez une recherche par mots-clés à la place."
    
    # Construire le prompt avec le contexte
    system_prompt = f"""
    Tu es un assistant spécialisé dans les parkings de Nantes Métropole.
    Tu as accès aux données de disponibilité des parkings à jour du {datetime.now().strftime('%d/%m/%Y à %H:%M')}.
    
    DONNÉES DES PARKINGS:
    {parking_data}
    
    INSTRUCTIONS:
    1. Réponds aux questions de l'utilisateur sur les parkings de Nantes.
    2. Propose les parkings les plus pertinents selon leur demande (proximité d'un lieu, disponibilité, etc.).
    3. Indique toujours le nombre de places disponibles et l'heure de dernière mise à jour quand c'est disponible.
    4. Mentionne les tarifs, horaires et informations spéciales quand c'est pertinent.
    5. Pour les parcs relais, précise les connexions aux transports en commun.
    6. Sois concis mais informatif.
    7. Ne mentionne pas que tu utilises des données au format JSON dans ta réponse.
    8. Si l'utilisateur demande des informations qui ne se trouvent pas dans les données, indique poliment que tu n'as pas cette information.
    9. Comprends que l'utilisateur parle en français et réponds-lui toujours en français.
    10. Si tu ne connais pas la disponibilité d'un parking, indique-le clairement.
    """
    
    # Construire les messages
    messages = []
    
    # Ajouter l'historique de conversation (jusqu'à 10 derniers messages pour limiter le contexte)
    for msg in conversation_history[-10:]:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    
    # Ajouter la nouvelle question
    messages.append({"role": "user", "content": user_query})
    
    # Préparer le payload pour l'API
    payload = {
        "model": "claude-3-haiku-20240307",
        "system": system_prompt,
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(
            CLAUDE_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extraire la réponse de l'IA
        if "content" in response_data and len(response_data["content"]) > 0:
            return response_data["content"][0]["text"]
        else:
            raise Exception("Format de réponse inattendu")
            
    except Exception as e:
        st.error(f"Erreur lors de l'appel à Claude API: {str(e)}")
        # Fallback à la recherche simple en cas d'échec
        return fallback_search(user_query, parking_data)

# Fonction de recherche de base (fallback) si Claude échoue
def fallback_search(query, parking_data):
    try:
        # Convertir les données JSON en liste d'objets
        if isinstance(parking_data, str):
            parkings = json.loads(parking_data)
        else:
            parkings = parking_data
        
        if not parkings:
            return "Aucune donnée de parking disponible pour la recherche."
        
        # Recherche simple
        query = query.lower()
        results = []
        
        # Rechercher dans les noms, adresses et types de parkings
        for parking in parkings:
            if (query in parking.get("nom", "").lower() or 
                query in parking.get("adresse", "").lower() or 
                query in parking.get("type", "").lower()):
                results.append(parking)
        
        if not results:
            # Si pas de résultats, chercher dans les disponibilités ou autre info
            for parking in parkings:
                if "disponibilite" in parking and parking["disponibilite"].get("places_disponibles", 0) > 0:
                    results.append(parking)
                    
        if not results:
            return f"Aucun parking trouvé pour '{query}'. Essayez avec d'autres termes comme 'centre-ville', 'gare', ou un nom de quartier."
        
        # Limiter les résultats et formater
        results = results[:5]  # Limiter à 5 résultats
        return format_parking_info(results)
            
    except Exception as e:
        return f"Erreur lors de la recherche: {str(e)}"

# Initialisation de la session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Message d'accueil
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Bonjour ! Je suis votre assistant IA pour les parkings de Nantes Métropole. Comment puis-je vous aider aujourd'hui ?"
    })

# Chargement et préparation des données (une seule fois par session ou tous les 5 minutes)
if "last_update" not in st.session_state or "parking_data" not in st.session_state or (datetime.now() - st.session_state.last_update).total_seconds() > 300:
    raw_data = fetch_all_parking_data()
    st.session_state.parking_data = prepare_parking_data(raw_data)
    st.session_state.last_update = datetime.now()
    st.session_state.raw_parking_data = raw_data  # Stocker aussi les données brutes pour l'affichage

# Affichage des messages précédents
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie pour l'utilisateur
user_input = st.chat_input("Posez votre question sur les parkings de Nantes...")

# Traitement de l'entrée utilisateur
if user_input:
    # Afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Obtenir la réponse de l'IA
    ai_response = ask_claude(user_input, st.session_state.parking_data, st.session_state.messages)
    
    # Afficher la réponse
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)

# Pied de page
st.markdown("---")
st.caption("Propulsé par l'IA Claude d'Anthropic • Données: Open Data Nantes Métropole")

# Sidebar avec informations et paramètres
with st.sidebar:
    st.header("À propos")
    st.markdown("""
    Ce chatbot utilise l'intelligence artificielle Claude pour vous aider à trouver des places de stationnement à Nantes Métropole.
    
    Exemples de questions:
    - "Où puis-je me garer près de la gare ?"
    - "Quels parkings ont des places disponibles dans le centre-ville ?"
    - "Y a-t-il des parcs relais avec accès au tramway ?"
    - "Quel est le tarif du parking Commerce ?"
    """)
    
    # Affichage de l'heure de la dernière mise à jour
    st.write(f"Dernière mise à jour des données: {st.session_state.last_update.strftime('%H:%M:%S')}")
    
    # Bouton pour rafraîchir les données
    if st.button("Rafraîchir les données"):
        raw_data = fetch_all_parking_data()
        st.session_state.parking_data = prepare_parking_data(raw_data)
        st.session_state.last_update = datetime.now()
        st.session_state.raw_parking_data = raw_data
        st.rerun()
    
    # Option pour effacer l'historique
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Conversation effacée. Comment puis-je vous aider avec les parkings de Nantes aujourd'hui ?"
        })
        st.rerun()
    
    # Affichage des statistiques globales
    st.header("Statistiques")
    
    if "raw_parking_data" in st.session_state:
        raw_data = st.session_state.raw_parking_data
        
        # Calculer les statistiques de disponibilité
        total_parkings = 0
        available_spaces = 0
        total_spaces = 0
        
        # Pour parkings publics
        if "parkings_disponibilites" in raw_data:
            for p in raw_data["parkings_disponibilites"]:
                if "grp_disponible" in p and "grp_exploitation" in p:
                    total_parkings += 1
                    available_spaces += p.get("grp_disponible", 0)
                    total_spaces += p.get("grp_exploitation", 0)
        
        # Pour parcs relais
        if "parcs_relais_disponibilites" in raw_data:
            for p in raw_data["parcs_relais_disponibilites"]:
                if "disponible" in p and "capacite" in p:
                    total_parkings += 1
                    available_spaces += p.get("disponible", 0)
                    total_spaces += p.get("capacite", 0)
        
        # Afficher les statistiques
        st.metric("Nombre de parkings", total_parkings)
        st.metric("Places disponibles", available_spaces)
        if total_spaces > 0:
            occupation_rate = 100 - (available_spaces / total_spaces * 100)
            st.metric("Taux d'occupation", f"{occupation_rate:.1f}%")
