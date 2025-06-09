import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv
import asyncio
from collections import Counter

load_dotenv()  # Carga las variables del archivo .env
TOKEN = os.getenv("DISCORD_TOKEN")

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

@bot.event
async def on_ready():
    # Mensaje en consola cuando el bot se conecta correctamente
    print(f"✅ Bot conectado como {bot.user.name}")

@bot.command()
async def ping(ctx):
    # Comando simple para comprobar si el bot está activo
    await ctx.send("🏓 ¡Estoy vivo!")

@bot.command(name="carta")
async def carta(ctx):
    # Da una carta aleatoria al usuario y la guarda en su colección
    user_id = str(ctx.author.id)
    carta = random.choice(cartas)
    colecciones.setdefault(user_id, []).append(carta["nombre"])
    guardar_colecciones()

    embed = discord.Embed(
        title="🎴 ¡Has recibido una carta!",
        description=f"**{carta['nombre']}**\n🔹 Tipo: {carta['tipo']}\n⭐ Rareza: {carta['rareza']}",
        color=discord.Color.gold()
    )
    if carta.get("imagen"):
        embed.set_image(url=carta["imagen"])

    embed.set_footer(text=f"{ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="coleccion")
async def coleccion(ctx):
    # Muestra todas las cartas que tiene el usuario en su colección
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, [])

    if not cartas_usuario:
        await ctx.send("📭 ¡Todavía no tienes ninguna carta!")
        return

    descripcion = "\n".join(f"• {nombre}" for nombre in cartas_usuario)
    embed = discord.Embed(
        title=f"📚 Colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name="ver")
async def ver_carta(ctx, *, nombre: str):
    # Permite buscar y ver detalles de una carta por nombre (parcial o completo)
    nombre = nombre.lower()
    coincidencias = [c for c in cartas if nombre in c["nombre"].lower()]

    if not coincidencias:
        await ctx.send(f"❌ No se encontró ninguna carta que coincida con **{nombre}**.")
        return

    if len(coincidencias) > 1:
        lista = "\n".join(f"• {c['nombre']}" for c in coincidencias)
        await ctx.send(
            f"🔍 Se encontraron varias cartas que coinciden con **{nombre}**:\n{lista}\n\n"
            f"🔁 Por favor, especifica mejor el nombre."
        )
        return

    carta = coincidencias[0]
    embed = discord.Embed(
        title=f"🃏 {carta['nombre']}",
        description=f"🔹 Tipo: {carta['tipo']}\n⭐ Rareza: {carta['rareza']}",
        color=discord.Color.purple()
    )
    if carta.get("imagen"):
        embed.set_image(url=carta["imagen"])

    embed.set_footer(text="Consulta de carta")
    await ctx.send(embed=embed)

@bot.command(name="sobre")
async def sobre(ctx):
    # Da al usuario un "sobre" con 3 cartas aleatorias (pueden repetirse)
    user_id = str(ctx.author.id)
    cartas_sobre = random.choices(cartas, k=3)

    colecciones.setdefault(user_id, [])
    for carta in cartas_sobre:
        colecciones[user_id].append(carta["nombre"])

    guardar_colecciones()

    embed = discord.Embed(
        title=f"🎁 ¡Has abierto un sobre con 3 cartas!",
        color=discord.Color.orange()
    )

    # Añade cada carta como campo en el embed
    for idx, carta in enumerate(cartas_sobre, 1):
        embed.add_field(
            name=f"Carta {idx}: {carta['nombre']}",
            value=f"🔹 Tipo: {carta['tipo']}\n⭐ Rareza: {carta['rareza']}",
            inline=False
        )

    # Muestra la imagen de la última carta del sobre
    if cartas_sobre[-1].get("imagen"):
        embed.set_image(url=cartas_sobre[-1]["imagen"])

    embed.set_footer(text=f"{ctx.author.display_name}")
    await ctx.send(embed=embed)

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

    if carta_mia not in colecciones.get(user1, []):
        await ctx.send(f"❌ No tienes la carta **{carta_mia}** para ofrecer.")
        return

    if carta_suya not in colecciones.get(user2, []):
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
        if carta_mia not in colecciones.get(user1, []):
            await ctx.send(f"❌ Ya no tienes la carta **{carta_mia}** para ofrecer.")
            return

        if carta_suya not in colecciones.get(user2, []):
            await ctx.send(f"❌ {jugador.display_name} ya no tiene la carta **{carta_suya}** para ofrecer.")
            return

        # Realiza el intercambio de cartas
        colecciones[user1].remove(carta_mia)
        colecciones[user2].remove(carta_suya)

        colecciones[user1].append(carta_suya)
        colecciones[user2].append(carta_mia)

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
    # Muestra un resumen de la colección del usuario, incluyendo cantidad total y rarezas
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, [])

    if not cartas_usuario:
        await ctx.send("❌ No tienes cartas en tu colección aún.")
        return

    # Contar rarezas de las cartas que tiene el usuario
    rarezas = []
    for nombre_carta in cartas_usuario:
        carta_info = next((c for c in cartas if c["nombre"] == nombre_carta), None)
        if carta_info:
            rarezas.append(carta_info["rareza"])
    conteo_rarezas = Counter(rarezas)

    # Total de cartas en la colección del usuario
    total = len(cartas_usuario)

    # Construye la descripción del resumen
    descripcion = f"Total cartas: **{total}**\n\n"
    descripcion += "📊 Distribución por rareza:\n"
    for rareza, cantidad in conteo_rarezas.most_common():
        descripcion += f"• {rareza}: {cantidad}\n"

    embed = discord.Embed(
        title=f"📚 Resumen de la colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.blue()
    )

    # Muestra hasta 10 cartas únicas de la colección como ejemplo
    cartas_unicas = sorted(set(cartas_usuario))
    lista_cartas = "\n".join(cartas_unicas[:10])
    if len(cartas_unicas) > 10:
        lista_cartas += "\n..."

    embed.add_field(name="Algunas cartas:", value=lista_cartas, inline=False)

    await ctx.send(embed=embed)

# Inicia el bot con el token de Discord
bot.run(TOKEN)
