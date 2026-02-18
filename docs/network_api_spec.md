# Spécification fonctionnelle — API Réseau WiFi

Source de vérité pour les tests. Tout comportement non décrit ici est hors scope ; les tests ne valident que ce document.

## 1. Contrat API

### 1.1 GET /network/current

- **Authentification** : JWT requis (en-tête `Authorization: Bearer <token>`). Sinon **401 Unauthorized**.
- **Succès (200)** : Corps JSON contenant exactement les champs suivants (types et nullabilité) :
  - `connected` (boolean)
  - `ssid` (string | null)
  - `signal` (integer | null ; si présent, valeur entre 0 et 100)
  - `security` (string | null)
  - `interface` (string, non vide)
  - `ip_address` (string | null)
  - `gateway` (string | null)
  - `mac_address` (string | null)
- **Erreur** : Si le sous-système réseau est indisponible → **503 Service Unavailable** avec corps contenant le détail de l’erreur (champ `detail` ou équivalent dans la structure d’erreur de l’API).

### 1.2 GET /network/list

- **Authentification** : JWT requis. Sinon **401**.
- **Succès (200)** : Tableau d’objets. Chaque élément contient :
  - Obligatoires : `ssid` (string), `signal` (integer), `security` (string)
  - Optionnels : `frequency` (integer | null), `channel` (integer | null), `bssid` (string | null)
- **Erreur** : Indisponibilité réseau → **503** avec détail.

### 1.3 POST /network/connect

- **Authentification** : JWT requis. Sinon **401**.
- **Autorisation** : Rôles **ADMIN** ou **SUPERADMIN** uniquement. Sinon **403 Forbidden** avec message explicite indiquant que seuls les administrateurs peuvent changer le réseau WiFi.
- **Corps (JSON)** : `ssid` (string, obligatoire), `password` (string | null), `hidden` (boolean, défaut false).
- **Succès (200)** : Corps avec `success` (true), `message` (string), `ssid` (string | null).
- **Échec de connexion** (mauvais mot de passe, réseau hors de portée, etc.) : **502 Bad Gateway** (ou 503 selon contexte), corps avec détail d’erreur. **Pas** de 200 avec `success: false`.
- **Indisponibilité** (ex. nmcli absent) : **503** avec détail.
- **Validation** : Body invalide (ex. ssid manquant) → **422 Unprocessable Entity**.

### 1.4 Règles générales

- Token expiré ou invalide → **401**.
- Codes HTTP exacts : 200, 401, 403, 422, 502, 503 selon les cas ci-dessus.
- Les réponses d’erreur HTTP (4xx/5xx) exposent un détail lisible (champ `detail` ou structure d’erreur de l’API).
