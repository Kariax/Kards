import discord
from discord.ext import commands
import random
import json
import os
from dotenv import load_dotenv
import asyncio
from collections import Counter
import unicodedata

# --- Configuración y utilidades globales ---

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
USUARIOS_AUTORIZADOS = ["189137793501364224", "1469686581873868822"]  # Reemplaza con los IDs de los usuarios autorizados

# Emojis y colores por rareza y tipo
EMOJIS_RAREZA = {"Común": "⚪", "Rara": "🔵", "Legendaria": "🟡"}
EMOJIS_TIPOS = {
    "Lugar": "🌍", "NPC": "👤", "Evento": "🎲",
    "Bestiario": "🐾", "Personaje": "🧙", "Objeto": "🗝️"
}
COLORES_RAREZA = {
    "Común": discord.Color.light_grey(),
    "Rara": discord.Color.dark_blue(),
    "Legendaria": discord.Color.gold()
}
ORDEN_RAREZA = ["Común", "Rara", "Legendaria"]

def quitar_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def cargar_colecciones():
    try:
        with open("colecciones.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_colecciones():
    with open("colecciones.json", "w", encoding="utf-8") as f:
        json.dump(colecciones, f, ensure_ascii=False, indent=2)

with open("cartas.json", "r", encoding="utf-8") as file:
    cartas = json.load(file)

colecciones = cargar_colecciones()

# Pesos de cartas por rareza
pesos_rarezas = {"Común": 60, "Rara": 30, "Legendaria": 10}
pesos_cartas = [pesos_rarezas.get(c["rareza"], 1) for c in cartas]

# --- Funciones utilitarias ---

def buscar_cartas_usuario(nombre, cartas, cartas_usuario):
    nombre_normalizado = quitar_tildes(nombre.lower())
    coincidencias = [
        c for c in cartas
        if quitar_tildes(c["nombre"].lower()).find(nombre_normalizado) != -1
        and cartas_usuario.get(c["nombre"], 0) > 0
    ]
    exacta = next(
        (c for c in cartas if quitar_tildes(c["nombre"].lower()) == nombre_normalizado and cartas_usuario.get(c["nombre"], 0) > 0),
        None
    )
    if exacta:
        return [exacta]
    return coincidencias

def crear_embed_carta(carta, usuario):
    color = COLORES_RAREZA.get(carta.get("rareza", ""), discord.Color.dark_grey())
    emoji_rareza = EMOJIS_RAREZA.get(carta.get("rareza", ""), "")
    emoji_tipo = EMOJIS_TIPOS.get(carta.get("tipo", ""), "")
    embed = discord.Embed(
        title=f"🃏 **`{carta['nombre'].upper()}`**",
        color=color
    )
    embed.add_field(name="🔹 Tipo", value=f"**{carta['tipo']}** {emoji_tipo}", inline=True)
    embed.add_field(name="⭐ Rareza", value=f"{emoji_rareza} **{carta['rareza']}** {emoji_rareza}", inline=True)
    embed.add_field(name="📝 Descripción", value=carta.get("descripcion", "Sin descripción."), inline=False)
    if carta.get("imagen"):
        embed.set_image(url=carta["imagen"])
    embed.set_footer(text=f"{usuario.display_name}")
    return embed

def agrupar_cartas_por_rareza(cartas_usuario):
    cartas_por_rareza = {rareza: [] for rareza in ORDEN_RAREZA}
    for nombre, cantidad in cartas_usuario.items():
        carta_info = next((c for c in cartas if c["nombre"] == nombre), None)
        if carta_info:
            rareza = carta_info.get("rareza", "Común")
            if rareza in cartas_por_rareza:
                cartas_por_rareza[rareza].append((nombre, cantidad, EMOJIS_RAREZA.get(rareza, "")))
    return cartas_por_rareza

# --- Bot setup ---

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user.name}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 ¡Estoy vivo!")


@bot.event
async def on_message(message):
    # Process commands from incoming messages.
    # If the message was sent by this bot, only process it when it starts with the command prefix ('!').
    # This allows webhook messages sent by the bot to trigger commands while avoiding most loops.
    try:
        content = message.content or ""
    except Exception:
        content = ""

    if content.lstrip().startswith("!"):
        try:
            ctx = await bot.get_context(message)
            if ctx.command is not None:
                try:
                    can_run = await ctx.command.can_run(ctx)
                except Exception:
                    can_run = False
                # If the message comes from a webhook or a bot and checks pass, invoke manually
                if (getattr(message, 'webhook_id', None) or getattr(message.author, 'bot', False)) and can_run:
                    try:
                        await bot.invoke(ctx)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    if message.author == bot.user:
        if not content.lstrip().startswith("!"):
            return

    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    try:
        await ctx.send(f"❌ Ocurrió un error ejecutando el comando: {error}")
    except Exception:
        pass

def solo_autorizado():
    def predicate(ctx):
        result = False
        try:
            # Direct authorized users
            if str(getattr(ctx.author, 'id', None)) in USUARIOS_AUTORIZADOS:
                result = True
            else:
                content = (ctx.message.content or "").lstrip()
                # Allow this bot (or webhooks) to invoke commands when the message starts with the prefix
                if ctx.author == bot.user and content.startswith("!"):
                    result = True
                if getattr(ctx.message, "webhook_id", None) and content.startswith("!"):
                    result = True
        except Exception:
            result = False
        return result
    return commands.check(predicate)


async def resolve_member(ctx, usuario_input):
    """Resolve a user input (mention, id, name) to a `discord.Member`.
    Returns `None` if not found.
    """
    if usuario_input is None:
        return ctx.author
    if isinstance(usuario_input, discord.Member):
        return usuario_input
    from discord.ext.commands import MemberConverter
    converter = MemberConverter()
    try:
        member = await converter.convert(ctx, str(usuario_input))
        return member
    except Exception:
        pass
    # Try extract numeric ID from the input
    import re
    m = re.search(r"(\d{17,20})", str(usuario_input))
    if m and ctx.guild:
        try:
            member = ctx.guild.get_member(int(m.group(1))) or await ctx.guild.fetch_member(int(m.group(1)))
            if member:
                return member
        except Exception:
            pass
    # Fallback: match by name or display_name
    if ctx.guild:
        for member in ctx.guild.members:
            if member.display_name == usuario_input or member.name == usuario_input:
                return member
    return None

# Función utilitaria para enviar errores como embed
async def enviar_error(ctx, mensaje):
    embed = discord.Embed(
        title="❌ Error",
        description=mensaje,
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name="carta")
@solo_autorizado()
async def carta(ctx, usuario_input: str = None):
    # Resolve the target member (accept mention, id, name, or None for author)
    usuario = await resolve_member(ctx, usuario_input)
    if usuario is None:
        await enviar_error(ctx, "No pude encontrar al usuario especificado.")
        return

    user_id = str(usuario.id)
    try:
        carta = random.choices(cartas, weights=pesos_cartas, k=1)[0]
    except Exception:
        await enviar_error(ctx, "No se pudo seleccionar una carta.")
        return
    colecciones.setdefault(user_id, {})
    colecciones[user_id][carta["nombre"]] = colecciones[user_id].get(carta["nombre"], 0) + 1
    guardar_colecciones()

    embed = crear_embed_carta(carta, usuario)
    await ctx.send(f"🎁 {usuario.mention} ha recibido una carta:", embed=embed)

@bot.command(name="sobre")
@solo_autorizado()
async def sobre(ctx, usuario_input: str = None):
    # Resolve the target member (accept mention, id, name, or None for author)
    usuario = await resolve_member(ctx, usuario_input)
    if usuario is None:
        await enviar_error(ctx, "No pude encontrar al usuario especificado.")
        return

    user_id = str(usuario.id)
    try:
        cartas_sobre = random.choices(cartas, weights=pesos_cartas, k=10)
    except Exception:
        await enviar_error(ctx, "No se pudo generar el sobre.")
        return
    colecciones.setdefault(user_id, {})
    for carta in cartas_sobre:
        colecciones[user_id][carta["nombre"]] = colecciones[user_id].get(carta["nombre"], 0) + 1
    guardar_colecciones()

    embed = discord.Embed(
        title=f"🎁 ¡Has abierto un sobre con 10 cartas!",
        color=discord.Color.orange()
    )
    for idx, carta in enumerate(cartas_sobre, 1):
        emoji_rareza = EMOJIS_RAREZA.get(carta.get("rareza", ""), "")
        emoji_tipo = EMOJIS_TIPOS.get(carta.get("tipo", ""), "")
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

@bot.command(name="coleccion")
async def coleccion(ctx, usuario: discord.Member = None):
    # Si no se especifica usuario, se usa el autor
    if usuario is None:
        usuario = ctx.author

    user_id = str(usuario.id)
    cartas_usuario = colecciones.get(user_id, {})
    if not cartas_usuario or not any(cartas_usuario.values()):
        await enviar_error(ctx, f"¡{usuario.display_name} todavía no tiene ninguna carta!")
        return

    # Cambia el orden de rarezas: Legendaria, Rara, Común
    ORDEN_RAREZA_INVERSO = ["Legendaria", "Rara", "Común"]
    cartas_por_rareza = agrupar_cartas_por_rareza(cartas_usuario)
    cartas_lista = []
    for rareza in ORDEN_RAREZA_INVERSO:
        cartas_r = cartas_por_rareza[rareza]
        for nombre, cantidad, emoji in cartas_r:
            if cantidad > 1:
                cartas_lista.append(f"{emoji} {nombre} x{cantidad}")
            else:
                cartas_lista.append(f"{emoji} {nombre}")

    cartas_por_pagina = 15
    paginas = [cartas_lista[i:i+cartas_por_pagina] for i in range(0, len(cartas_lista), cartas_por_pagina)]
    total_paginas = len(paginas)
    if total_paginas == 0:
        paginas = [["(Vacío)"]]
        total_paginas = 1

    def crear_embed_pagina(pagina_idx):
        descripcion = "\n".join(paginas[pagina_idx])
        embed = discord.Embed(
            title=f"📚 Colección de {usuario.display_name} (Página {pagina_idx+1}/{total_paginas})",
            description=descripcion,
            color=discord.Color.purple()
        )
        return embed

    pagina_actual = 0
    mensaje = await ctx.send(embed=crear_embed_pagina(pagina_actual))

    if total_paginas > 1:
        await mensaje.add_reaction("⬅️")
        await mensaje.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == mensaje.id
            )

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                break

            if str(reaction.emoji) == "➡️" and pagina_actual < total_paginas - 1:
                pagina_actual += 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "⬅️" and pagina_actual > 0:
                pagina_actual -= 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            else:
                await mensaje.remove_reaction(reaction, user)

@bot.command(name="ver")
async def ver_carta(ctx, *, nombre: str):
    user_id = str(ctx.author.id)
    cartas_usuario = colecciones.get(user_id, {})

    coincidencias = buscar_cartas_usuario(nombre, cartas, cartas_usuario)

    if not coincidencias:
        await enviar_error(ctx, "Solo puedes ver cartas que posees en tu colección.")
        return

    if len(coincidencias) > 1:
        lista = "\n".join(f"• {c['nombre']}" for c in coincidencias)
        await enviar_error(
            f"Se encontraron varias cartas que coinciden con ese nombre en tu colección:\n{lista}\n\n"
            f"🔁 Por favor, especifica mejor el nombre."
        )
        return

    carta = coincidencias[0]
    embed = crear_embed_carta(carta, ctx.author)
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
        await enviar_error(ctx, "No tienes cartas en tu colección aún.")
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

    descripcion = "📊 **Progreso de colección por rareza:**\n\n"
    total_obtenidas = 0
    total_cartas = 0
    for rareza in orden_rareza:
        cartas_set = rarezas_totales.get(rareza, set())
        obtenidas = len(rarezas_usuario.get(rareza, set()))
        total = len(cartas_set)
        porcentaje = (obtenidas / total * 100) if total > 0 else 0
        emoji = emojis_rareza.get(rareza, "")
        descripcion += f"{emoji} {rareza}: {obtenidas}/{total} ({porcentaje:.1f}%)\n"
        total_obtenidas += obtenidas
        total_cartas += total

    # Porcentaje total
    porcentaje_total = (total_obtenidas / total_cartas * 100) if total_cartas > 0 else 0
    descripcion += f"\n📈 **Total colección:** `{total_obtenidas}/{total_cartas} ({porcentaje_total:.1f}%)`"

    embed = discord.Embed(
        title=f"📚 Estado de la colección de {ctx.author.display_name}",
        description=descripcion,
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)

@bot.command(name="falta")
async def faltantes(ctx, usuario: discord.Member = None):
    # Si no se especifica usuario, se usa el autor
    if usuario is None:
        usuario = ctx.author

    user_id = str(usuario.id)
    cartas_usuario = colecciones.get(user_id, {})

    # Obtén los nombres de todas las cartas y las que tiene el usuario
    todas_las_cartas = set(c["nombre"] for c in cartas)
    cartas_tenidas = set(nombre for nombre, cantidad in cartas_usuario.items() if cantidad > 0)
    cartas_faltantes = todas_las_cartas - cartas_tenidas

    if not cartas_faltantes:
        await ctx.send(f"🎉 ¡{usuario.display_name} tiene la colección completa!")
        return

    # Ordena por rareza (Legendaria, Rara, Común) y luego alfabéticamente
    faltantes_ordenados = []
    orden_rareza = ["Común", "Rara", "Legendaria"]
    for rareza in orden_rareza:
        nombres = sorted(
            [c["nombre"] for c in cartas if c["nombre"] in cartas_faltantes and c["rareza"] == rareza]
        )
        for nombre in nombres:
            emoji = EMOJIS_RAREZA.get(rareza, "")
            faltantes_ordenados.append(f"{emoji} {nombre}")

    cartas_por_pagina = 15
    paginas = [faltantes_ordenados[i:i+cartas_por_pagina] for i in range(0, len(faltantes_ordenados), cartas_por_pagina)]
    total_paginas = len(paginas)
    if total_paginas == 0:
        paginas = [["(Vacío)"]]
        total_paginas = 1

    def crear_embed_pagina(pagina_idx):
        descripcion = "\n".join(paginas[pagina_idx])
        embed = discord.Embed(
            title=f"🗂️ Cartas que le faltan a {usuario.display_name} (Página {pagina_idx+1}/{total_paginas})",
            description=descripcion,
            color=discord.Color.orange()
        )
        return embed

    pagina_actual = 0
    mensaje = await ctx.send(embed=crear_embed_pagina(pagina_actual))

    if total_paginas > 1:
        await mensaje.add_reaction("⬅️")
        await mensaje.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == mensaje.id
            )

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                break

            if str(reaction.emoji) == "➡️" and pagina_actual < total_paginas - 1:
                pagina_actual += 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "⬅️" and pagina_actual > 0:
                pagina_actual -= 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            else:
                await mensaje.remove_reaction(reaction, user)

# Comando para comparar colecciones entre dos usuarios
@bot.command(name="comparar")
async def comparar(ctx, usuario: discord.Member = None):
    """
    Compara la colección del autor con la de otro usuario y muestra:
    - Cartas que el autor tiene y el otro no.
    - Cartas que el otro tiene y el autor no.
    Mostrando la cantidad de cada carta que tiene cada usuario.
    """
    if usuario is None:
        await enviar_error(ctx, "Debes mencionar a otro usuario para comparar colecciones. Ejemplo: `!comparar @usuario`")
        return

    if usuario.id == ctx.author.id:
        await enviar_error(ctx, "No puedes comparar tu colección contigo mismo.")
        return

    user1_id = str(ctx.author.id)
    user2_id = str(usuario.id)
    coleccion1 = colecciones.get(user1_id, {})
    coleccion2 = colecciones.get(user2_id, {})
    cartas_user1 = set(nombre for nombre, cantidad in coleccion1.items() if cantidad > 0)
    cartas_user2 = set(nombre for nombre, cantidad in coleccion2.items() if cantidad > 0)

    if not cartas_user1:
        await enviar_error(ctx, f"{ctx.author.display_name} no tiene cartas en su colección.")
        return
    if not cartas_user2:
        await enviar_error(ctx, f"{usuario.display_name} no tiene cartas en su colección.")
        return

    solo_user1 = cartas_user1 - cartas_user2
    solo_user2 = cartas_user2 - cartas_user1

    def lista_cartas(nombres, coleccion):
        # Ordena por rareza y luego alfabéticamente
        orden_rareza = ["Legendaria", "Rara", "Común"]
        resultado = []
        for rareza in orden_rareza:
            nombres_rareza = sorted(
                [c["nombre"] for c in cartas if c["nombre"] in nombres and c["rareza"] == rareza]
            )
            for nombre in nombres_rareza:
                emoji = EMOJIS_RAREZA.get(rareza, "")
                cantidad = coleccion.get(nombre, 0)
                resultado.append(f"{emoji} {nombre} x{cantidad}")
        return resultado if resultado else ["(Ninguna)"]

    paginas = [
        {
            "titulo": f"✅ Cartas que **{ctx.author.display_name}** tiene y **{usuario.display_name}** no",
            "contenido": lista_cartas(solo_user1, coleccion1)
        },
        {
            "titulo": f"✅ Cartas que **{usuario.display_name}** tiene y **{ctx.author.display_name}** no",
            "contenido": lista_cartas(solo_user2, coleccion2)
        }
    ]
    total_paginas = len(paginas)

    def crear_embed_pagina(idx):
        embed = discord.Embed(
            title=f"🔍 Comparación de colecciones",
            description=f"{ctx.author.display_name} vs {usuario.display_name}",
            color=discord.Color.teal()
        )
        embed.add_field(
            name=paginas[idx]["titulo"],
            value="\n".join(paginas[idx]["contenido"])[:1024],
            inline=False
        )
        embed.set_footer(text=f"Página {idx+1}/{total_paginas}")
        return embed

    pagina_actual = 0
    mensaje = await ctx.send(embed=crear_embed_pagina(pagina_actual))

    if total_paginas > 1:
        await mensaje.add_reaction("⬅️")
        await mensaje.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == mensaje.id
            )

        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                break

            if str(reaction.emoji) == "➡️" and pagina_actual < total_paginas - 1:
                pagina_actual += 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "⬅️" and pagina_actual > 0:
                pagina_actual -= 1
                await mensaje.edit(embed=crear_embed_pagina(pagina_actual))
                await mensaje.remove_reaction(reaction, user)
            else:
                await mensaje.remove_reaction(reaction, user)

# Sobrescribe el comando help por defecto antes de definir el tuyo
bot.remove_command("help")

@bot.command(name="help")
async def help_command(ctx):
    descripcion = (
        "**Comandos disponibles:**\n\n"
        "• `!ping` — Comprueba si el bot está activo.\n"
        "• `!coleccion [@usuario]` — Muestra la colección de cartas de un usuario (o la tuya si no mencionas a nadie), con paginación.\n"
        "• `!ver <nombre>` — Muestra información detallada de una carta que posees. Ejemplo: `!ver goblin`\n"
        "• `!intercambiar @usuario \"mi_carta\" \"su_carta\"` — Propón un intercambio de cartas con otro usuario. Ejemplo: `!intercambiar @Kariax \"Goblin\" \"Lobo\"`\n"
        "• `!resumen` — Muestra un resumen de tu colección y la distribución de rarezas.\n"
        "• `!falta [@usuario]` — Muestra las cartas que te faltan para completar la colección (o las de otro usuario), con paginación.\n"
        "• `!comparar @usuario` — Compara tu colección con la de otro usuario y muestra las diferencias.\n"
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