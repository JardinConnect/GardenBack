🚀 Commandes utiles ALEMBIC
Action	Commande
Générer une migration	alembic revision --autogenerate -m "titre de ton changement de migration"
Appliquer les migrations	alembic upgrade head
Revenir à la version précédente	alembic downgrade -1
Voir l’historique	alembic history