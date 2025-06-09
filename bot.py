import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv
import asyncio
from collections import Counter

load_dotenv()  # Carga las variables desde .env
TOKEN = os.getenv("DISCORD_TOKEN")

# Funciones para leer y guardar colecciones
def cargar_colecciones():
    try:
        with open("colecciones.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_colecciones():
    with open("colecciones.json", "w", encoding="utf-8") as f:
        json.dump(colecciones, f, ensure_ascii=False, indent=2)

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Leer cartas desde JSON
with open("cartas.json", "r", encoding="utf-8") as file:
    cartas = json.load(file)

# Leer colecciones guardadas
colecciones = cargar_colecciones()

# Intents y configuración del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user.name}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 ¡Estoy vivo!")

@bot.command(name="carta")
async def carta(ctx):
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
    nombre = nombre.lower()
    
    # Buscar cartas cuyo nombre contenga el fragmento ingresado
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
    user_id = str(ctx.author.id)
    cartas_sobre = random.choices(cartas, k=3)  # 3 cartas aleatorias (con posible repetición)

    colecciones.setdefault(user_id, [])
    for carta in cartas_sobre:
        colecciones[user_id].append(carta["nombre"])

    guardar_colecciones()

    embed = discord.Embed(
        title=f"🎁 ¡Has abierto un sobre con 3 cartas!",
        color=discord.Color.orange()
    )
    
    # Agregar cada carta como campo en el embed con su imagen (imagen como thumbnail en embed no es múltiple, ponemos al final la del último)
    for idx, carta in enumerate(cartas_sobre, 1):
        embed.add_field(
            name=f"Carta {idx}: {carta['nombre']}",
            value=f"🔹 Tipo: {carta['tipo']}\n⭐ Rareza: {carta['rareza']}",
            inline=False
        )
    
    # Imagen del último ítem para ilustrar el sobre (Discord no permite varias imágenes)
    if cartas_sobre[-1].get("imagen"):
        embed.set_image(url=cartas_sobre[-1]["imagen"])

    embed.set_footer(text=f"{ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="intercambiar")
async def intercambiar(ctx, jugador: discord.Member, carta_mia: str, carta_suya: str):
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

    # Enviar mensaje de confirmación a jugador2
    confirm_msg = await ctx.send(
        f"🤝 {jugador.mention}, {ctx.author.display_name} te propone intercambiar:\n"
        f"• Él da: **{carta_mia}**\n"
        f"• Tú das: **{carta_suya}**\n\n"
        f"Reacciona ✅ para aceptar o ❌ para cancelar. (30 segundos)"
    )

    # Añadir reacciones para que el jugador reaccione
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
        # Confirmar que ambos aún tienen las cartas (puede que hayan cambiado)
        if carta_mia not in colecciones.get(user1, []):
            await ctx.send(f"❌ Ya no tienes la carta **{carta_mia}** para ofrecer.")
            return

        if carta_suya not in colecciones.get(user2, []):
            await ctx.send(f"❌ {jugador.display_name} ya no tiene la carta **{carta_suya}** para ofrecer.")
            return

        # Realizar intercambio
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
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, [])

    if not cartas_usuario:
        await ctx.send("❌ No tienes cartas en tu colección aún.")
        return

    # Contar rarezas
    rarezas = [c["rareza"] for c in cartas if c["nombre"] in cartas_usuario]
    conteo_rarezas = Counter(rarezas)

    # Total cartas
    total = len(cartas_usuario)

    # Construir texto del embed
    descripcion = f"Total cartas: **{total}**\n\n"
    descripcion += "📊 Distribución por rareza:\n"
    for rareza, cantidad in conteo_rarezas.most_common():
        descripcion += f"• {rareza}: {cantidad}\n"

    embed = discord.Embed(
        title=f"📚 Resumen de la colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.blue()
    )

    # Opcional: mostrar hasta 10 cartas en lista
    cartas_unicas = sorted(set(cartas_usuario))
    lista_cartas = "\n".join(cartas_unicas[:10])
    if len(cartas_unicas) > 10:
        lista_cartas += "\n..."

    embed.add_field(name="Algunas cartas:", value=lista_cartas, inline=False)

    await ctx.send(embed=embed)

bot.run(TOKEN)
