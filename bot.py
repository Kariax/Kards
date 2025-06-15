import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv
import asyncio
from collections import Counter
import unicodedata

load_dotenv()  # Carga las variables del archivo .env
TOKEN = os.getenv("DISCORD_TOKEN")

# Reemplaza "TU_ID_AQUI" por tu ID real de usuario de Discord (por ejemplo: "189137793501364224")
USUARIO_AUTORIZADO = "189137793501364224"

# Función para leer las colecciones de cartas de los usuarios desde el archivo JSON
def cargar_colecciones():
    try:
        with open("colecciones.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Si el archivo no existe, retorna un diccionario vacío
        return {}

# Función para guardar las colecciones de cartas de los usuarios en el archivo JSON
def guardar_colecciones():
    with open("colecciones.json", "w", encoding="utf-8") as f:
        json.dump(colecciones, f, ensure_ascii=False, indent=2)

# Carga las cartas disponibles desde el archivo JSON
with open("cartas.json", "r", encoding="utf-8") as file:
    cartas = json.load(file)

# Carga las colecciones de los usuarios
colecciones = cargar_colecciones()

# Configuración de los intents para el bot de Discord (solo los necesarios)
intents = discord.Intents.default()
intents.members = True  # Para comandos que usan miembros (como intercambiar)
intents.message_content = True  # Para leer el contenido de los mensajes

bot = commands.Bot(command_prefix="!", intents=intents)

# Define los pesos por rareza (ajusta los valores según lo raro que quieras cada tipo)
pesos_rarezas = {
    "Común": 60,
    "Rara": 30,
    "Legendaria": 10
}

# Calcula los pesos para cada carta al cargar el archivo de cartas
pesos_cartas = [pesos_rarezas.get(c["rareza"], 1) for c in cartas]

# Colores por rareza para el borde del embed (ajusta si lo deseas)
colores_rarezas = {
    "Común": discord.Color.light_grey(),
    "Rara": discord.Color.dark_blue(),
    "Legendaria": discord.Color.gold()
}

# Emojis por rareza para mostrar junto al texto de rareza
emojis_rarezas = {
    "Común": "⚪",
    "Rara": "🔵",
    "Legendaria": "🟡"
}

# Emojis por tipo de carta
emojis_tipos = {
    "Lugar": "🌍",
    "NPC": "👤",
    "Evento": "🎲",
    "Bestiario": "🐾",
    "Personaje": "🧙",
    "Objeto": "🗝️"
}

def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

@bot.event
async def on_ready():
    # Mensaje en consola cuando el bot se conecta correctamente
    print(f"✅ Bot conectado como {bot.user.name}")

@bot.command()
async def ping(ctx):
    # Comando simple para comprobar si el bot está activo
    await ctx.send("🏓 ¡Estoy vivo!")

@bot.command(name="carta")
async def carta(ctx, usuario: discord.Member = None):
    # Si no se especifica usuario, se usa el autor
    if usuario is None:
        usuario = ctx.author

    # Solo el usuario autorizado puede usar el comando
    if str(ctx.author.id) != USUARIO_AUTORIZADO:
        await ctx.send("❌ Solo el usuario autorizado puede usar este comando.")
        return

    user_id = str(usuario.id)
    carta = random.choices(cartas, weights=pesos_cartas, k=1)[0]
    colecciones.setdefault(user_id, {})
    colecciones[user_id][carta["nombre"]] = colecciones[user_id].get(carta["nombre"], 0) + 1
    guardar_colecciones()

    color = colores_rarezas.get(carta.get("rareza", ""), discord.Color.gold())
    emoji_rareza = emojis_rarezas.get(carta.get("rareza", ""), "")
    emoji_tipo = emojis_tipos.get(carta.get("tipo", ""), "")

    embed = discord.Embed(
        title="🎴 ¡Has recibido una carta!",
        description=(
            f"**`{carta['nombre'].upper()}`**\n"
            f"🔹 Tipo: **{carta['tipo']}** {emoji_tipo}\n"
            f"⭐ Rareza: {emoji_rareza} **{carta['rareza']}** {emoji_rareza}\n"
            f"📝 {carta.get('descripcion', 'Sin descripción.')}"
        ),
        color=color  # Color de borde según rareza
    )
    if carta.get("imagen"):
        embed.set_image(url=carta["imagen"])

    embed.set_footer(text=f"{usuario.display_name}")
    await ctx.send(f"🎁 {usuario.mention} ha recibido una carta:", embed=embed)

@bot.command(name="coleccion")
async def coleccion(ctx):
    global cartas

    # Muestra todas las cartas que tiene el usuario en su colección, agrupando repetidas
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, {})

    if not cartas_usuario or not any(cartas_usuario.values()):
        await ctx.send("📭 ¡Todavía no tienes ninguna carta!")
        return

    # Orden de rarezas y sus emojis
    orden_rareza = ["Común", "Rara", "Legendaria"]
    emojis_rareza = {
        "Común": "⚪",
        "Rara": "🔵",
        "Legendaria": "🟡"
    }

    # Agrupa cartas por rareza
    cartas_por_rareza = {rareza: [] for rareza in orden_rareza}
    for nombre, cantidad in cartas_usuario.items():
        carta_info = next((c for c in cartas if c["nombre"] == nombre), None)
        if carta_info:
            rareza = carta_info.get("rareza", "Común")
            if rareza in cartas_por_rareza:
                cartas_por_rareza[rareza].append((nombre, cantidad, emojis_rareza.get(rareza, "")))

    # Construye la descripción solo con cartas y emoji de rareza, sin titular de rareza
    descripcion = ""
    for rareza in orden_rareza:
        cartas_r = cartas_por_rareza[rareza]
        for nombre, cantidad, emoji in cartas_r:
            if cantidad > 1:
                descripcion += f"{emoji} {nombre} x{cantidad}\n"
            else:
                descripcion += f"{emoji} {nombre}\n"

    embed = discord.Embed(
        title=f"📚 Colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command(name="ver")
async def ver_carta(ctx, *, nombre: str):
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, {})

    # Normaliza el nombre buscado (sin tildes y minúsculas)
    nombre_normalizado = quitar_tildes(nombre.lower())

    # Busca coincidencias ignorando tildes y mayúsculas/minúsculas
    coincidencias = [
        c for c in cartas
        if quitar_tildes(c["nombre"].lower()).find(nombre_normalizado) != -1
    ]

    # Buscar coincidencia exacta primero
    exacta = next(
        (c for c in cartas if quitar_tildes(c["nombre"].lower()) == nombre_normalizado),
        None
    )
    if exacta:
        coincidencias = [exacta]

    # Filtra solo cartas que el usuario posee
    coincidencias = [
        c for c in coincidencias
        if c["nombre"] in cartas_usuario and cartas_usuario[c["nombre"]] > 0
    ]

    if not coincidencias:
        await ctx.send("❌ Solo puedes ver cartas que posees en tu colección.")
        return

    if len(coincidencias) > 1:
        lista = "\n".join(f"• {c['nombre']}" for c in coincidencias)
        await ctx.send(
            f"🔍 Se encontraron varias cartas que coinciden con ese nombre en tu colección:\n{lista}\n\n"
            f"🔁 Por favor, especifica mejor el nombre."
        )
        return

    carta = coincidencias[0]

    # Colores por rareza
    colores_rarezas = {
        "Común": discord.Color.light_grey(),
        "Rara": discord.Color.blue(),
        "Legendaria": discord.Color.gold()
    }
    color = colores_rarezas.get(carta.get("rareza", ""), discord.Color.dark_grey())

    emoji_rareza = emojis_rarezas.get(carta.get("rareza", ""), "")
    emoji_tipo = emojis_tipos.get(carta.get("tipo", ""), "")

    embed = discord.Embed(
        title=f"🃏 **`{carta['nombre'].upper()}`**",
        color=color
    )
    embed.add_field(name="🔹 Tipo", value=f"**{carta['tipo']}** {emoji_tipo}", inline=True)
    embed.add_field(name="⭐ Rareza", value=f"{emoji_rareza} **{carta['rareza']}** {emoji_rareza}", inline=True)
    embed.add_field(name="📝 Descripción", value=carta.get("descripcion", "Sin descripción."), inline=False)

    if carta.get("imagen"):
        embed.set_image(url=carta["imagen"])

    embed.set_footer(text="Consulta de carta")
    await ctx.send(embed=embed)

@bot.command(name="sobre")
async def sobre(ctx, usuario: discord.Member = None):
    # Si no se especifica usuario, se usa el autor
    if usuario is None:
        usuario = ctx.author

    # Solo el usuario autorizado puede usar el comando
    if str(ctx.author.id) != USUARIO_AUTORIZADO:
        await ctx.send("❌ Solo el usuario autorizado puede usar este comando.")
        return
    # Da 10 cartas aleatorias al usuario (pueden repetirse)

    user_id = str(usuario.id)
    cartas_sobre = random.choices(cartas, weights=pesos_cartas, k=10)

    colecciones.setdefault(user_id, {})
    for carta in cartas_sobre:
        colecciones[user_id][carta["nombre"]] = colecciones[user_id].get(carta["nombre"], 0) + 1

    guardar_colecciones()

    embed = discord.Embed(
        title=f"🎁 ¡Has abierto un sobre con 10 cartas!",
        color=discord.Color.orange()
    )

    # Añade cada carta como campo en el embed, sin mostrar imágenes
    for idx, carta in enumerate(cartas_sobre, 1):
        color = colores_rarezas.get(carta.get("rareza", ""), discord.Color.gold())
        emoji_rareza = emojis_rarezas.get(carta.get("rareza", ""), "")
        emoji_tipo = emojis_tipos.get(carta.get("tipo", ""), "")
        embed.add_field(
            name=f"Carta {idx}: **`{carta['nombre'].upper()}`**",
            value=(
                f"🔹 Tipo: **{carta['tipo']}** {emoji_tipo}\n"
                f"⭐ Rareza: {emoji_rareza} **{carta['rareza']}** {emoji_rareza}\n"
                f"📝 {carta.get('descripcion', 'Sin descripción.')}"
            ),
            inline=False
        )

    embed.set_footer(text=f"{usuario.display_name}")
    await ctx.send(f"🎁 {usuario.mention} ha recibido un sobre:", embed=embed)

@bot.command(name="intercambiar")
async def intercambiar(ctx, jugador: discord.Member, carta_mia: str, carta_suya: str):
    # Permite intercambiar cartas entre dos usuarios con confirmación por reacción
    user1 = str(ctx.author.id)
    user2 = str(jugador.id)

    if user1 == user2:
        await ctx.send("❌ No puedes intercambiar cartas contigo mismo.")
        return

    carta_mia = carta_mia.strip()
    carta_suya = carta_suya.strip()

    # Verifica que ambos usuarios tengan la carta y al menos 1 unidad
    if colecciones.get(user1, {}).get(carta_mia, 0) < 1:
        await ctx.send(f"❌ No tienes la carta **{carta_mia}** para ofrecer.")
        return

    if colecciones.get(user2, {}).get(carta_suya, 0) < 1:
        await ctx.send(f"❌ {jugador.display_name} no tiene la carta **{carta_suya}** para ofrecer.")
        return

    # Solicita confirmación al segundo usuario mediante reacciones
    confirm_msg = await ctx.send(
        f"🤝 {jugador.mention}, {ctx.author.display_name} te propone intercambiar:\n"
        f"• Él da: **{carta_mia}**\n"
        f"• Tú das: **{carta_suya}**\n\n"
        f"Reacciona ✅ para aceptar o ❌ para cancelar. (30 segundos)"
    )

    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return (
            user == jugador
            and reaction.message.id == confirm_msg.id
            and str(reaction.emoji) in ["✅", "❌"]
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send(f"⌛ El intercambio fue cancelado por falta de respuesta de {jugador.display_name}.")
        return

    if str(reaction.emoji) == "✅":
        # Verifica que ambos usuarios aún tengan las cartas antes de intercambiar
        if colecciones.get(user1, {}).get(carta_mia, 0) < 1:
            await ctx.send(f"❌ Ya no tienes la carta **{carta_mia}** para ofrecer.")
            return

        if colecciones.get(user2, {}).get(carta_suya, 0) < 1:
            await ctx.send(f"❌ {jugador.display_name} ya no tiene la carta **{carta_suya}** para ofrecer.")
            return

        # Realiza el intercambio de cartas
        colecciones[user1][carta_mia] -= 1
        if colecciones[user1][carta_mia] == 0:
            del colecciones[user1][carta_mia]
        colecciones[user2][carta_suya] -= 1
        if colecciones[user2][carta_suya] == 0:
            del colecciones[user2][carta_suya]

        colecciones[user1][carta_suya] = colecciones[user1].get(carta_suya, 0) + 1
        colecciones[user2][carta_mia] = colecciones[user2].get(carta_mia, 0) + 1

        guardar_colecciones()

        await ctx.send(
            f"✅ Intercambio realizado entre {ctx.author.display_name} y {jugador.display_name}:\n"
            f"• {ctx.author.display_name} entregó **{carta_mia}** y recibió **{carta_suya}**\n"
            f"• {jugador.display_name} entregó **{carta_suya}** y recibió **{carta_mia}**"
        )
    else:
        await ctx.send(f"❌ {jugador.display_name} canceló el intercambio.")

@bot.command(name="resumen")
async def resumen(ctx):
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, {})

    if not cartas_usuario or not any(cartas_usuario.values()):
        await ctx.send("❌ No tienes cartas en tu colección aún.")
        return

    # Calcula el total de cartas únicas por rareza en la colección del usuario
    rarezas_usuario = {}
    for nombre_carta in cartas_usuario.keys():
        carta_info = next((c for c in cartas if c["nombre"] == nombre_carta), None)
        if carta_info:
            rareza = carta_info["rareza"]
            rarezas_usuario.setdefault(rareza, set()).add(nombre_carta)

    # Calcula el total de cartas únicas por rareza existentes en el juego
    rarezas_totales = {}
    for carta in cartas:
        rareza = carta["rareza"]
        rarezas_totales.setdefault(rareza, set()).add(carta["nombre"])

    # Orden y emojis de rareza
    orden_rareza = ["Común", "Rara", "Legendaria"]
    emojis_rareza = {
        "Común": "⚪",
        "Rara": "🔵",
        "Legendaria": "🟡"
    }

    descripcion = "📊 **Progreso de colección por rareza:**\n"
    for rareza in orden_rareza:
        cartas_set = rarezas_totales.get(rareza, set())
        obtenidas = len(rarezas_usuario.get(rareza, set()))
        total = len(cartas_set)
        porcentaje = (obtenidas / total * 100) if total > 0 else 0
        emoji = emojis_rareza.get(rareza, "")
        descripcion += f"{emoji} {rareza}: {obtenidas}/{total} ({porcentaje:.1f}%)\n"

    embed = discord.Embed(
        title=f"📚 Estado de la colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)

# Sobrescribe el comando help por defecto antes de definir el tuyo
bot.remove_command("help")

@bot.command(name="help")
async def help_command(ctx):
    """
    Muestra una ayuda con la explicación de todos los comandos disponibles.
    """
    descripcion = (
        "**Comandos disponibles:**\n\n"
        "• `!ping` — Comprueba si el bot está activo.\n"
        "• `!coleccion` — Muestra todas las cartas que tienes en tu colección.\n"
        "• `!ver <nombre>` — Muestra información detallada de una carta (puedes usar parte del nombre).\n"
        "• `!intercambiar @usuario \"nombre_mi_carta\" \"nombre_su_carta\"` — Propón un intercambio de cartas (nombre exacto) con otro usuario.\n"
        "• `!resumen` — Muestra un resumen de tu colección y la distribución de rarezas.\n"
        "• `!help` — Muestra este mensaje de ayuda.\n"
    )
    embed = discord.Embed(
        title="ℹ️ Ayuda de Kards",
        description=descripcion,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Inicia el bot con el token de Discord
bot.run(TOKEN)