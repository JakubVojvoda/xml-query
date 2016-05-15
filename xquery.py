#!/usr/bin/python3.2
#
# XML Query in Python 3
# by Jakub Vojvoda [vojvoda@swdeveloper.sk]
# 2013
#

import sys, re, os
import xml.dom.minidom
from xml.dom.minidom import parse, parseString, Node 

# Navratove hodnoty
E_SUCCESS = 0
WRONG_PARAMS = 1
INPUT_ERROR = 2
OUTPUT_ERROR = 3
IN_FORMAT = 4
SELECT_ERR = 80

# Spracovanie parametrov prikazovej riadky
# navratove hodnoty: 
#       0 - vsetko prebehlo v poriadku
#       1 - bol zadany parameter --help
#       2 - nespravny format alebo neznamy parameter
def argshandle ():
  i = 1
  
  # premenne pre vyvarovanie sa opakovania parametrov
  query_input = 1
  global qf_or_query
  p_i = 0
  p_o = 0
  p_n = 0
  p_r = 0
  
  # kontrola cez vsetky zadane parametre
  while ( i < len(sys.argv) ):
    
    # napoveda
    if ( re.match( r"--help", sys.argv[i])):
      if ( len(sys.argv) != 2):
        return 2
      return 1
    
    # parameter --input=...
    elif ( re.match( r"--input=.+", sys.argv[i]) and p_i == 0):
      global input_filename
      # vyber cesty k suboru
      input_filename = os.path.abspath(sys.argv[i][8:])
      p_i += 1
    
    # parameter --output=...
    elif ( re.match( r"--output=.+", sys.argv[i]) and p_o == 0):
      global output_filename
      # vyber cesty k suboru
      output_filename = os.path.abspath(sys.argv[i][9:])
      p_o += 1
    
    # parameter --query=...
    elif ( re.match( r"--qf=.+", sys.argv[i]) and query_input):
      global query_filename
      # vyber cesty k suboru
      query_filename = os.path.abspath(sys.argv[i][5:])
      # premenne k zabraneniu zadania 2 dotazov --query a --qf sucatne
      query_input = 0
      qf_or_query = 1
    
    # parameter --qf=...
    elif ( re.match( r"--query=[^']+", sys.argv[i]) and query_input):
      global qf_content
      # uloz zadany dotaz
      qf_content = sys.argv[i][8:]
      # premenne k zabraneniu zadania 2 dotazov --query a --qf sucatne
      query_input = 0
      qf_or_query = 2
  
    # parameter -n
    elif ( re.match( r"-n", sys.argv[i]) and p_n == 0):
      global option_n
      option_n = 1
      p_n += 1
    
    # parameter --root=...
    elif ( re.match( r"--root=.+", sys.argv[i]) and p_r == 0):
      global root_element
      # uloz zadany nazov korenoveho elementu
      root_element = sys.argv[i][7:]
      p_r += 1
    
    # nespravny alebo neznamy parameter
    else:
      return 2
  
    i += 1
  return E_SUCCESS
# ---------------------------------------------------------

# Kontrola syntaxe zadaneho dotazu 
# - dotaz je ulozeny v globalnej premmenej 'qf_content'  
# - kontrola spravnosti s vyuzitim regularneho vyrazu
# - navratove hodnoty
#       0 - vsetko v poriadku
#       1 - syntakticka chyba
def correctness_check():
  # Regularny vyraz na overenie korektnosti syntaxe dotazu 
  syntax_regex = "SELECT [a-zA-Z_][a-zA-Z0-9_\-:]* (LIMIT [0-9]+ )?FROM "
  syntax_regex += "(ROOT|(([a-zA-Z_][a-zA-Z0-9_\-:]*)|(([a-zA-Z_][a-zA-Z0-9_\-:]*)?.[a-zA-Z_][a-zA-Z0-9_\-:]*)))"
  syntax_regex += "( WHERE (\(+|\)+|NOT|AND|OR|((([a-zA-Z_][a-zA-Z0-9_\-:]*)|(([a-zA-Z_][a-zA-Z0-9_\-:]*)?.[a-zA-Z_][a-zA-Z0-9_\-:]*))"
  syntax_regex += " (CONTAINS|=|>|<) ((\"[^\s\t\n\r\\\"]*\")|([0-9]+))))+)?"
  syntax_regex += "(\s+ORDER BY (([a-zA-Z_][a-zA-Z0-9_\-:]*)|(([a-zA-Z_][a-zA-Z0-9_\-:]*)?.[a-zA-Z_][a-zA-Z0-9_\-:]*)) (ASC|DESC))?\s*"
  
  # Ak je zadany parameter --qf=filename, uloz obsah suboru
  # do globalnej premmenej qf_content
  if (qf_or_query == 1):
    try:
      q_file = open(query_filename, "r")
    except IOError:
      sys.stderr.write("xqr: query: cannot open file\n")
      sys.exit(INPUT_ERROR)
    
    global qf_content
    qf_content = q_file.read()
    q_file.close()
  
  # kontrola syntaxe dotazu
  syntax_match = re.match( syntax_regex,  qf_content)
  
  # syntakticka chyba
  if not syntax_match:
    return 1
  
  return E_SUCCESS
# ---------------------------------------------------------

# Extrahuj polozky zo zadaneho syntakticky spravneho dotazu
# - funkcia vracia: 
#    slovnik (dict) jednotlivych poloziek dotazu
#       (select, limit, from_type, from, where, order)
#    ak polozka neexistuje vrati 'None'
def query_extract(qf_content): 
  
  # odstranenie poslednych znakov '\n' alebo ' ' ak existuju 
  qtmp = qf_content[-1:]
  
  if (qtmp == '\n' or qtmp == ' '):
    i = -1
    # zistenie poctu bielych znakov k odstraneniu
    while qf_content[i-1:i] == '\n' or qf_content[i-1:i] == ' ':
      i -= 1
    
    qtmp = qf_content[:i]
    qf_content = qtmp
  
  # vyber poloziek z dotazu
  qh, qrest = qf_content.split(" FROM ")
  
  # ak dotaz obsahuje klauzulu LIMIT, vyberu sa polozky
  qs = qh[7:]
  qfind = qs.find("LIMIT")
  
  if (qfind != -1):
    qselect, qlimit = qs.split(" LIMIT ")
  else:
    qselect = qs
    qlimit = -1
  
  # vyhladanie, ci sa v dotaze nachadza klauzula
  # WHERE alebo ORDER BY
  qfind1 = qrest.find(" WHERE ")
  qfind2 = qrest.find("ORDER BY ")
  
  # najdene WHERE aj ORDER BY
  if (qfind1 != -1 and qfind2 != -1):
    qfrom, qr = qrest.split(" WHERE ")
    qw, qorder = qr.split("ORDER BY ")
    try:  
      qwhere, qwhere_z = qw.split('\n')
    except: 
      qwhere = qw
    
  # najdene len WHERE
  elif (qfind1 != -1 and qfind2 == -1):
    qfrom, qwhere = qrest.split(" WHERE ")
    qorder = None
  
  # najdene len ORDER BY
  elif (qfind1 == -1 and qfind2 != -1):
    qfrom, qorder = qrest.split(" ORDER BY ")
    qwhere = None    
  
  # nenajdene WHERE ani ORDER BY
  elif (qfind1 == -1 and qfind2 == -1):
    qfrom = qrest
    qwhere = None
    qorder = None
  
  # urcenie typu v klauzule FROM
  # - FROM ROOT
  if ( qfrom == "ROOT"):
    qfrom_type = 0
  # element
  elif ( re.match("^[a-zA-Z_][a-zA-Z0-9_\-:]*$", qfrom)):
    qfrom_type = 1
  # .attribute
  elif ( re.match("^.[a-zA-Z_][a-zA-Z0-9_\-:]*$", qfrom)):
    qfrom_type = 2
  # element.attribute
  elif ( re.match("^[a-zA-Z_][a-zA-Z0-9_\-:]*.[a-zA-Z_][a-zA-Z0-9_\-:]*$", qfrom)):
    qfrom_type = 3
  # neznamy typ
  else:
    qfrom_type = -1
  
  return qselect, qlimit, qfrom_type, qfrom, qwhere, qorder
# ---------------------------------------------------------

# Funkcia vybere prvy element s atributom 'attr'
# Prehladavanie do hlbky
# Funkcia vrati prvy najdeny element alebo None
def item_attribute(element, attr):
  
  # hlbka zanorenia
  depth = 0
  
  while element != None:
    # ak element obsahuje pozadovany atribut, tak je vrateny
    if element.nodeType != 3 and element.hasAttribute and element.getAttribute(attr):
      return element
    # ak nie je element text, zanor sa hlbsie
    elif element.nodeType != 3:
      element = element.firstChild
      depth += 1
    # ak je element text, otestuj, ci je posledny v aktualnom zanoreni
    # ak ano vynor sa o stupen vyssie 
    # ak nie posun sa na dalsi element
    elif element.nodeType == 3:
      new_element = element.nextSibling
      
      if new_element == None:
        c = depth
        for i in range(1, c):
          element = element.parentNode
          depth -= 1
          tmp = element.nextSibling
          
          if tmp != None:
            break
            
        element = element.nextSibling
      else:
        element = new_element
# ---------------------------------------------------------

# Otestuje je zadany element 'str_element', ci neobsahuje
# elementy ine ako textove
# Funkcia pri najdeni netextoveho elementu zastavi vykonavanie
# skriptu a na stderr vypise chybove hlasenie
def check_node_type(str_element, data):
  
  count = 0
  
  for element in data.getElementsByTagName(str_element):
    # prejdi vsetky podelementy v danom elemente
    for node in element.childNodes:
      if node.nodeType != 3:
        count += 1
  
  if count > 0:
    sys.stderr.write("xqr: input: wrong input file format\n")
    sys.exit(IN_FORMAT)
# ---------------------------------------------------------

# Funkcia vykonava vyber elementov odpovedajucich dotazu
# zo vstupneho XML suboru
# Vracia slovnik (dict) vyhovujucich elementov
# ak narazi na chybu, v prvej polozke slovnika vrati:
#    -1: syntakticka/semanticka chyba
#     4: nespravny format vstupneho suboru

# Ako parametre ocakava:
#   query: slovnik poloziek odpovedajucich klauzule select-from
#   idata: vstupny XML dokument
#   qwhere: slovnik poloziek odpovedajucich klauzule where
def select_from( query, idata, qwhere):
  # vyuziva slovnik
  sel = {}
  i = 0
  
  # SELECT element FROM ROOT
  if (query[2] == 0 and qwhere == None):
    for node in idata.getElementsByTagName(query[0]):
      sel[i] = node
      i += 1
  
  # SELECT element FROM element
  elif (query[2] == 1 and qwhere == None):
    for node in idata.getElementsByTagName(query[3]):
      for n in node.getElementsByTagName(query[0]):
        sel[i] = n
        i += 1
      break
  
  # SELECT element FROM .attribute
  elif (query[2] == 2 and qwhere == None):
    try:
      elem, attr = query[3].split(".")    
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR)
      
    el = idata.firstChild
    s = item_attribute(el, attr)
    
    # nenajdeny ziaden vyhovujuci .atribut, vrati prazdny slovnik  
    if s == None:
      return {}
    
    for n in s.getElementsByTagName(query[0]):
      sel[i] = n
      i += 1
    
  # SELECT element FROM element.atribute
  elif (query[2] == 3 and qwhere == None):
    try:
      elem, attr = query[3].split(".")
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR)
    
    for node in idata.getElementsByTagName(elem):
      n = node.getAttributeNode(attr)
      if (n != None):
        for s in node.getElementsByTagName(query[0]):
          sel[i] = s
          i += 1
        break
        
  # SELECT element FROM ROOT WHERE condition
  elif (query[2] == 0 and qwhere != None):
    for node in idata.getElementsByTagName(query[0]):
      # call rutine for check where condition
      errn = use_where(qwhere, node)
      check_node_type(qwhere[1][2:], idata)
      if errn == 0:
        sel[i] = node
        i += 1
      elif errn == 4 or errn == -1:
        sel[0] = errn
        return sel
  
  # SELECT element FROM element WHERE condition
  elif (query[2] == 1 and qwhere != None):
    for node in idata.getElementsByTagName(query[3]):
      for n in node.getElementsByTagName(query[0]):
        
        # funkcia overi ci element 'n' vyhovuje klauzule where
        errn = use_where(qwhere, n)
        check_node_type(qwhere[1][2:], idata)
        
        if errn == 0:
          sel[i] = n
          i += 1
        elif errn == 4 or errn == -1:
          sel[0] = errn
          return sel
      break
  
  # SELECT element FROM .attribute WHERE condition
  elif (query[2] == 2 and qwhere != None):
    
    try:
      elem, attr = query[3].split(".")    
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR)
    
    el = idata.firstChild
    s = item_attribute(el, attr)
    
    if s == None:
      return {}
    
    for n in s.getElementsByTagName(query[0]):
      # call rutine for check where condition
      errn = use_where(qwhere, n)
      check_node_type(qwhere[1][2:], idata)
      if errn == 0:
        sel[i] = n
        i += 1
      elif errn == 4 or errn == -1:
        sel[0] = errn
        return sel
  
  # SELECT element FROM element.attribute WHERE condition
  elif (query[2] == 3 and qwhere != None):
    
    try:
      elem, attr = query[3].split(".")
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR)
    
    for node in idata.getElementsByTagName(elem):
      n = node.getAttributeNode(attr)
      if (n != None):
        for s in node.getElementsByTagName(query[0]):
          # call rutine for check where condition
          errn = use_where(qwhere, s)
          check_node_type(qwhere[1][2:], idata)
          if errn == 0:
            sel[i] = s
            i += 1
          elif errn == 4 or errn == -1:
            sel[0] = errn
            return sel
        break
  
  return sel
# ---------------------------------------------------------

# Upravy pocet poloziek na pocet odpovedajuci klauzule LIMIT
# Funkcia vrati upraveny slovnik poloziek
# alebo slovnik bez zmien, ak klauzula LIMIT nie je zadana alebo 
# ak je pozadovany pocet vacsi ako pocet prvkov
def edit_limit(items, limit):
  
  # klauzula LIMIT neexistuje
  if limit == -1:
    return items
  
  # slovnik, urceny k vrateniu z funkcie
  new_items = {}
  i = 0
  
  length = len(items)
  
  # skopiruje sa len mozny pocet poloziek
  if length < limit:
    limit = length
  
  while i < limit:
    new_items[i] = items[i]
    i += 1
  
  return new_items
# ---------------------------------------------------------

# Funkcia vyberie potrebne polozky z klauzule WHERE
# a pritom overuje ich syntakticku spravnost
# Funkcia vracia:
#     None: ak doslo k chybe
#     slovnik poloziek ak kontrola prebehla v poriadku
def parse_where(qwhere):
  
  clausule = {}
  counter = 0
  l = len(qwhere)
  i = 0
  
  # prechod cez celu klauzulu
  while i < l:
    
    # vlozi relacne operatory do slovnika
    if qwhere[i] == '=' or qwhere[i] == '>' or qwhere[i] == '<':
      clausule[counter] = qwhere[i]
      counter += 1
      i += 1
    
    # '*' je zastupny symbol pre CONTAINS
    elif qwhere[i:i+8] == 'CONTAINS':
      clausule[counter] = '*'
      counter += 1
      i += 8
      
    # '^' je zastupny symbol pre NOT
    elif qwhere[i:i+3] == 'NOT':
      clausule[counter] = '^'
      counter += 1
      i += 3
    
    # vlozi cislo do slovnika
    elif re.match( r"[0-9]", qwhere[i]) or (qwhere[i] == '-' and (i+1 < l)  and re.match(r"[0-9]", qwhere[i+1])):
      fr = i
      i += 1
      
      while i < l and re.match( r"[0-9.]", qwhere[i]):
        i += 1
      
      clausule[counter] = qwhere[fr:i]
      counter += 1
    
    # vlozi retazec do slovnika
    elif qwhere[i] == '"':
      fr = i
      i += 1
      
      while i < l and qwhere[i] != '"':
        i += 1
        
      i += 1
      clausule[counter] = qwhere[fr:i]
      counter += 1
    
    # ak sa narazi na .atribut, je pridana znacka '2#'
    elif qwhere[i] == '.':
      fr = i
      i += 1
      
      while i < l and re.match(r"[a-zA-Z0-9_\-:]", qwhere[i]):
        i += 1
      
      clausule[counter] = "2#" + qwhere[fr:i]
      counter += 1
    
    # ak element.attribute, je pridana znacka '3#'
    # ak element, znacka '1#'
    elif re.match( r"[a-zA-Z_]", qwhere[i]):
      fr = i
      sign = ''
      
      while i < l and re.match(r"[a-zA-Z0-9_\-:\.]", qwhere[i]):
        if qwhere[i] == '.':
          sign = "3#"
        i += 1
      
      if sign == '':
        sign = "1#"
      
      clausule[counter] = sign + qwhere[fr:i]
      counter += 1
    
    # preskocenie vsetkych medzier
    elif qwhere[i] == ' ':
      i += 1
    
    # syntakticka chyba
    else:
      return None
  
  return clausule
# ---------------------------------------------------------

# Funkcia otestuje semanticku spravnost klauzule where
# Na vstupe ocakava slovnik 'qwhere' syntakticky spravnych poloziek
# Funkcia vrati:
#    0: ak prebehla kontrola v poriadku
#  > 0 : ak sa jedna o semanticku chybu
def check_where_semantic(qwhere):
  
  l = len(qwhere)
  
  for i in range(0, l):
    
    # po <ELEM-OR-ATTR> moze nasledovat <REL-OPERATOR>
    if qwhere[i][:2] == '1#' or qwhere[i][:2] == '2#' or qwhere[i][:2] == '3#':
      # element/attribute cannot by last item
      if l <= i + 1:
        return 1
      x = qwhere[i+1]
      if x != '=' and x != '>' and x != '<' and x != '*':
        return 1
    
    # po <REL-OPERATOR> okrem CONTAINS, moze nasledovat <LITERAL>
    elif qwhere[i] == '=' or qwhere[i] == '>' or qwhere[i] == '<':
      # relation operator cannot by last item
      if l <= i + 1:
        return 1
      x = qwhere[i+1]
      if not re.match(r"\"[^\"]*\"", x) and not re.match(r"-?[0-9.]+", x):
        return 2
    
    # po CONTAINS moze nasledovat <LITERAL> okrem cisla
    elif qwhere[i] == '*':
      # CONTAINS cannot by last item
      if l == i + 1:
        return 1
      x = qwhere[i+1]
      if not re.match(r"\"[^\"]*\"", x):
        return 3
    
    # <ELEM-OR-ATTR> nesmie byt poslednou polozkou v klauzule
    elif re.match(r"\"[^\"]*\"", qwhere[i]) or re.match(r"-?[0-9.]+", qwhere[i]):
      if i != l - 1:
        return 4
    
    # po NOT moze nasledovat <ELEM-OR-ATTR>
    elif qwhere[i] == '^':
      # NOT nesmie byt poslednou polozkou
      if l <= i + 1:
        return 1
      x = qwhere[i+1]
      if not re.match(r"\"[^\"]*\"", x) and not re.match(r"-?[0-9.]+", x) and x != '^':
        return 5  
        
  return 0
# ---------------------------------------------------------

# Odstrani prebytocne NOT v klauzule WHERE 
# Ako parameter ocakava slovnik syntakticky semanticky
# korektnych poloziek klauzule WHERE 'qwhere'
# Funkcia vrati slovnik bez redundantnych operatorov NOT
def remove_not(qwhere):
  
  new_qwhere = {}
  length = len(qwhere)
  i = 0  
  
  # v klauzule sa nachadza minimalne jeden NOT
  if qwhere[0] == '^':
    
    # pocet NOT v klauzule
    while qwhere[i] == '^':
      i += 1
    
    # spocitanie, ci sa jedna o parny alebo neparny pocet
    remainder = i % 2
    
    # parny pocet NOT, odpovedajuca polozka bude None   
    if remainder == 0:
      new_qwhere[0] = None
    # neparny pocet NOT, odpovedajuca polozka bude NOT
    else:
      new_qwhere[0] = '^'
      
  else:
    # ak klauzula where neobsahuje NOT, polozka bude None
    new_qwhere[0] = None
  
  # prekopirovanie ostatnych poloziek bez redundantych NOT
  for x in range(1, length - i + 1):
      new_qwhere[x] = qwhere[x + i - 1] 
    
  return new_qwhere
# ---------------------------------------------------------
  
# Funkcia vybere elementy odpovedajuce klauzule WHERE
# Ako parameter je ocakavany slovnik poloziek klauzule where 'qwhere' 
# a data nad ktorymi sa ma vyber vykonat.
# Funkcia vracia:
#   0: ak data odpovedaju klauzule  
#   1: ak neodpovedaju
#  -1: syntakticka/semanticka chyba
#   4: nespravny format vstupu 'data'
def use_where(qwhere, data):
  
  # WHERE <NOT> <ELL-OR-ATTR> <REL-OPERATOR> <LITERAL>
  
  # ak nazov vstupnych dat je rovnaky ako pozadovany data
  # a zarroven su to textove data pokracuj vo vyhodnoteni
  if data.tagName == qwhere[1][2:]:
    
    if data.firstChild.nodeType != 3:
      return 4
    
    ch = str(data.firstChild.data)
    
    
  # <ELL-OR-ATTR> is element
  elif qwhere[1][:2] == '1#':
    node = data.getElementsByTagName(qwhere[1][2:])
    
    # ak neexistuje pozadovany element
    if node == [] and qwhere[0] == None:
      return 1
    elif node == [] and qwhere[0] == '^':
      return 0
      
    node = node[0]
    
    if node.firstChild.nodeType != 3:
      return 4
    ch = node.firstChild.data
    
    if ch == "":
      return 1
  
  # <ELL-OR-ATTR> je .atribut
  elif qwhere[1][:2] == '2#':
    ch = data.getAttribute(qwhere[1][3:])
    # vyber element s danym atributom
    if ch == "":
      el = data.firstChild
      ch = item_attribute(el , qwhere[1][3:])
        
      if ch != None:
        ch = ch.getAttribute(qwhere[1][3:])
      elif ch == None and qwhere[0] == '^':
        return 0
      else:
        return 1
      
    # ak nie je najdeny ziadny vyhovujuci element
    # (element s danym atributom neexistuje)
    if ch == "" and qwhere[0] == None:
      return 1
    if ch == "" and qwhere[0] == '^':
      return 0
  
  # <ELL-OR-ATTR> je element.atribut
  elif qwhere[1][:2] == '3#':
    try:
      el, attr = qwhere[1][2:].split(".")
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR) 
      
    ch = ""
    for node in data.getElementsByTagName(el):
      ch = node.getAttribute(attr)
      if ch != "":
        break
    
    # ak pozadovany element s pozadovanym atributom
    # neexistuje
    if ch == "" and qwhere[0] == None:
      return 1
    if ch == "" and qwhere[0] == '^':
      return 0
  
  # neznamy <ELL-OR-ATTR>
  else:
    return -1

  # klauzula neobsahuje NOT - <NOT> je None
  if qwhere[0] == None:
    # <REL-OPERATOR> je '=' a <LITERAL> je cislo
    if re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '=':
      try:
        float(ch)
      except:
        return 1
      if float(ch) == float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je '<' a <LITERAL> je cislo
    elif re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '<':
      try:
        float(ch)
      except:
        return 1
      if float(ch) < float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je '>' a <LITERAL> je cislo
    elif re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '>':
      try:
        float(ch)
      except:
        return 1
      if float(ch) > float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je 'CONTAINS' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '*':
      if qwhere[3][1:-1] in ch:
        return 0
      return 1
    
    # <REL-OPERATOR> je '=' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '=':
      if ch == qwhere[3][1:-1]:
        return 0
      return 1
    
    # <REL-OPERATOR> je '<' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '<':
      if ch < qwhere[3][1:-1]:
        return 0
      return 1
    
    # <REL-OPERATOR> je '>' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '>':
      if ch > qwhere[3][1:-1]:
        return 0
      return 1
    
    # semanticka chyba
    else:
      return -1
  
  # klauzula obsahuje NOT
  elif qwhere[0] == '^':
    # <REL-OPERATOR> je '=' a <LITERAL> je cislo
    if re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '=':
      try:
        float(ch)
      except:
        return 1
      if float(ch) != float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je '<' a <LITERAL> je cislo
    elif re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '<':
      try:
        float(ch)
      except:
        return 1
      if float(ch) >= float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je '>' a <LITERAL> je cislo
    elif re.match(r"-?[0-9\.]+", qwhere[3]) and qwhere[2] == '>':
      try:
        float(ch)
      except:
        return 1
      if float(ch) <= float(qwhere[3]):
        return 0
      return 1
    
    # <REL-OPERATOR> je 'CONTAINS' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '*':
      if qwhere[3][1:-1] not in ch:
        return 0
      return 1
    
    # <REL-OPERATOR> je '=' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '=':
      if ch != qwhere[3][1:-1]:
        return 0
      return 1
    
    # <REL-OPERATOR> je '<' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '<':
      if ch >= qwhere[3][1:-1]:
        return 0
      return 1
    
    # <REL-OPERATOR> je '>' a <LITERAL> je retazec
    elif re.match(r"\"[^\"]*\"", qwhere[3]) and qwhere[2] == '>':
      if ch <= qwhere[3][1:-1]:
        return 0
      return 1
    
    # semanticka chyba
    else:
      return -1  
# ---------------------------------------------------------

# Vybere potrebne polozky z klauzule ORDER BY
# Funkcia vracia:
#   - slovnik syntakticky/semanticky spravnych poloziek
#   - None, ak doslo chybe z hladiska syntaxe/semantiky
def parse_orderby( qorder):
  
  clausule = {}
  counter = 0
  l = len(qorder)
  i = 0
  
  # prechod cez vsetky polozky klauzule
  while i < l:
    
    # najdeny je .atribut
    if qorder[i] == '.':
      fr = i
      i += 1
      
      while i < l and re.match(r"[a-zA-Z0-9_\-:]", qorder[i]):
        i += 1
      # pridana znacka atributu
      clausule[counter] = "2#" + qorder[fr:i]
      counter += 1
    
    # najdeny je typ zoradenia - zostupne
    elif qorder[i:i+4] == 'DESC':
      # zastupny symbol
      clausule[counter] = 'D'
      counter += 1
      i += 4
    
    # najdeny je typ zoradenia - zostupne
    elif qorder[i:i+3] == 'ASC':
      # zastupny symbol
      clausule[counter] = 'A'
      counter += 1
      i += 3
    
    # najdeny je element alebo element.atribut
    elif re.match( r"[a-zA-Z_]", qorder[i]):
      fr = i
      sign = ''
      
      while i < l and re.match(r"[a-zA-Z0-9_\-:\.]", qorder[i]):
        # znacka pre element.atribut
        if qorder[i] == '.':
          sign = "3#"
        i += 1
      # znacka pre element
      if sign == '':
        sign = "1#"
      
      clausule[counter] = sign + qorder[fr:i]
      counter += 1
    
    # preskocenie vsetkych medzier
    elif qorder[i] == ' ':
      i += 1
    
    # neznama/nekorektna polozka
    else:
      return None
  
  
  # vysledny slovnik obsahuje 2 polozky:
  #     element|.atribut|element.atribut a typ zoradenia
  l = len(clausule)
  if l != 2:
    return None
  
  if clausule[0][:2] != '1#' and clausule[0][:2] != '2#' and clausule[0][:2] != '3#':
    return None
  
  if clausule[1] != 'A' and clausule[1] != 'D':
    return None
  
  return clausule
# ---------------------------------------------------------

# Pomocna funkcia vyuzivajuca sa pri zoradeni ORDER BY
# Funkcia vrati overi polozky, ci splnaju obmedzenia klauzule ORDER BY
def give_item( data, qorder):
  
  err_code = 0
  # pozadovana polozka je element
  if qorder[0][:2] == '1#':
    node = data.getElementsByTagName(qorder[0][2:])
    if node == []:
      return ""
    else:
      node = node[0]
    
    if node.firstChild == None:  
      return ""
    elif node.firstChild.nodeType != 3:
      err_code = 4
      ch = ""
    else:
      ch = node.firstChild.data
  # pozadovana polozka je .atribut
  elif qorder[0][:2] == '2#':
    ch = data.getAttribute(qorder[0][3:])
    
    if ch == None:
      return ""
  # pozadovana polozka je element.atribut
  elif qorder[0][:2] == '3#':
    try:
      el, attr = qorder[0][2:].split(".")
    except ValueError:
      sys.stderr.write("xqr: query: syntax/semantic error\n")
      sys.exit(SELECT_ERR) 
    
    ch = ""
    for node in data.getElementsByTagName(el):
      ch = node.getAttribute(attr)
      if ch != "":
        break
    
    if ch == None:
      return ""
  # pozadovana polozka nesplnuje kriteria
  else:
    err_code = -1
  
  if err_code == 4:
    sys.stderr.write("xqr: input: wrong input file format\n")
    sys.exit(IN_FORMAT)
  elif err_code == -1:
    sys.stderr.write("xqr: order by: syntax/semantic error\n")
    sys.exit(SELECT_ERR)
    
  return ch
# ---------------------------------------------------------

# Funkcia zoradi slovnik elementov 'sel' podla poloziek
# v klauzule ORDER BY, premenna 'order'
# Funkcia vrati:
#    - zoradeni slovnik elementov
#    - None, v pripade chyby
def use_order( sel, order):
  
  l = len(sel)
  elem_or_attr = {}
  
  # Overenie elementov, ci splnaju kriteria klauzule ORDER BY 
  for i in range(0, l):
    elem_or_attr[i] = give_item( sel[i], order)
    
  # Zistenie, ci sa budu radit retazce alebo cisla 
  string = 0
  try:
    for i in range(0, l):
      float(elem_or_attr[i])
  except:
    string = 1
  
  # jedna sa o radenie retazcov
  if string == 1:
    sor = sorted(elem_or_attr.items(), key=lambda t:t[1])
  
  # jedna sa o radenie cisel
  else:  
    # zistenie ci sa jedna o cele alebo desatinne cislo
    integer = 1
    try:
      for i in range(0, l):
        int(elem_or_attr)
    except:
      integer = 0
    
    maximum = 0
    
    # ak sa jedna o desatinne cislo, prevod na cele cislo
    # s vynasobenim kazdeho cisla s rovnakou konstantou 
    if integer == 0:
      # vypocet konstanty - 10 ** max(dlzka desatinnej casti)
      for i in range(0, l):
        c, d = elem_or_attr[i].split('.')
        ex = len(d)
        maximum = max(maximum, ex)
      
      for i in range(0, l):
        elem_or_attr[i] = float(elem_or_attr[i]) * (10**maximum) 
        elem_or_attr[i] = int(elem_or_attr[i])
    
    # zoradenie celych cisel
    sor = sorted(elem_or_attr.items(), key=lambda t:t[1])
  
  new_sel = {}
  counter = 0
  # pre zjednodusenie prace, prekopirovanie poloziek
  # zo zoradeneho zoznamu do slovnika
  for index, item in enumerate(sor):
    for i in range(0, l):  
      
      if item[0] == i:
        new_sel[counter] = sel[i]
        counter += 1
  
  # nastala chyba pri kopirovani
  # v slovniku nie su vsetky polozky
  if len(new_sel) != l:
    return None
  
  # vzostupne radenie
  if order[1] == 'A':
    return new_sel
  
  # zostupne radenie - prehodenie poradie poloziek
  elif order[1] == 'D':
    tmp = new_sel
    l = len(new_sel)
    new_sel = {}
    
    for i in range(0, l):
      new_sel[i] = tmp[l-i-1]
    
    return new_sel
  
  return None
# ---------------------------------------------------------

# Funkcia prida atribut 'order' do kazdeho elementu
# zo slovniku
# Funkcia ako parametre ocakava:
#   - slovnik elementov
#   - XML vstup - vyzaduje metoda createAttribute(nazov)
# Funkcia vracia modifikovany slovnik
# Pouzita k ocislovaniu poloziek po zoradeni ORDER BY
def add_attribute(sel, idata):
  
  l = len(sel)
  
  for i in range(0, l):
    # vytvorenie atributu a pridanie cisla
    attr = idata.createAttribute('order')
    attr.value = str(i+1)
    sel[i].setAttributeNode(attr)
   
  return sel
# ---------------------------------------------------------



if __name__=='__main__':
  
  # Globalne premenne pre uchovanie vstupnych paramentrov
  input_filename = ""
  output_filename = ""
  query_filename = ""
  qf_content = ""
  option_n = 0
  root_element = ""

  # ak --query=... ako parameter premenna je rovna 1
  # if --qf=... ako parameter premenna je rovna 2
  qf_or_query = 0;
  
  # Napoveda
  phelp =  "Python script: XQR - XML Query\n"
  phelp += "Author: xvojvo00@stud.fit.vutbr.cz\n"
  phelp += "Usage:\n"
  phelp += " --help             print this help\n"
  phelp += " --input=filename   input XML file\n"
  phelp += " --output=filename  output XML file\n"  
  phelp += " --query='dotaz'    xml query\n"
  phelp += " --qf=filename      xml query\n"
  phelp += " -n                 no header on output\n"
  phelp += " --root=element     add root element on output\n"
  phelp += "All parameters are optional.\n"
  phelp += "Parameters --qf=filename and --query='dotaz'\n"
  phelp += "cannot be combinated.\n"
  
  # Spracovanie paramentrov prikazovej riadky
  arg = argshandle()
  
  if (arg == 1):
    print(phelp)
    sys.exit(E_SUCCESS)
  elif (arg == 2):
    sys.stderr.write("xqr: failed on command line arguments\n")
    sys.exit(WRONG_PARAMS)
  
  if qf_or_query == 0:
    sys.stderr.write("xqr: failed on command line arguments\n")
    sys.exit(WRONG_PARAMS)
  
  # Overenie syntaktickej spravnosti dotazu
  corr = correctness_check()
  
  if corr:
    sys.stderr.write("xqr: query: syntax/semantic error\n")
    sys.exit(SELECT_ERR)
  
  # Spracovanie dotazu
  query = query_extract(qf_content)
  
  if query[2] == -1:
    sys.stderr.write("xqr: query: syntax/semantic error\n")
    sys.exit(SELECT_ERR)
  
  # Otvorenie vstupneho suboru
  if (input_filename != ""):
    try:
      i_file = open(input_filename, "r")
    except IOError:
      sys.stderr.write("xqr: input: cannot open file\n")
      sys.exit(INPUT_ERROR)
    
    # Spracovanie vstupneho suboru
    try:
      idata = parse(i_file)
    except:
      sys.stderr.write("xqr: input: wrong input file format\n")
      sys.exit(IN_FORMAT)
    
  # Citanie vstupu z stdin, ak nie je zadany parameter --input=...
  else:
    
    try:
      iof_data = sys.stdin.read()
    except:
      sys.stderr.write("xqr: input: read failed\n")
      sys.exit(INPUT_ERROR)
    
    try:
      idata = parseString(iof_data)
    except:
      sys.stderr.write("xqr: input: wrong input file format\n")
      sys.exit(IN_FORMAT)
  
  # Spracovanie klauzule WHERE
  if query[4] != None:
    qwhere = parse_where( query[4])
    
    if qwhere == None:
      sys.stderr.write("xqr: parse where clausule: failed\n")
      sys.exit(SELECT_ERR)
    
    # Overenie spravnost klauzule WHERE
    correct = check_where_semantic( qwhere)
  
    if correct:
      sys.stderr.write("xqr: query: "+ str(correct) +" syntax/semantic error\n")
      sys.exit(SELECT_ERR)
    # Odstranenie redundantnych NOT
    qwhere = remove_not(qwhere)
    
  else:
    qwhere = None
  # Vyhodnotenie klauzule SELECT-FROM
  sel = select_from( query, idata, qwhere)
  
  if sel != {} and sel[0] == 4:
    sys.stderr.write("xqr: input: wrong input file format\n")
    sys.exit(IN_FORMAT)
  elif sel != {} and sel[0] == -1:
    sys.stderr.write("xqr: query: syntax/semantic error\n")
    sys.exit(SELECT_ERR) 
  
  # Ak je zadana klauzula ORDER BY
  if query[5] != None:
    order = {}
    # Spracovanie klauzule ORDER BY
    order = parse_orderby( query[5])
    
    if order == None:
      sys.stderr.write("xqr: order by: syntax/semantic error\n")
      sys.exit(SELECT_ERR)
    
    # Vyhodnotenie klauzule ORDER BY
    sel = use_order( sel, order)
    # Pridanie atributov, ktore urcuju poradie elementov
    sel = add_attribute( sel, idata)
  
  # Uprava poctu elementov, na pocet uvedeny v klauzule LIMIT
  # ak klauzule LIMIT nie je zadana - bez zmeny
  sel = edit_limit( sel, int(query[1]))
  
  # Vystupne dokument
  xmlout = ""
  
  # Pridanie XML hlavicky
  if option_n == 0:
    xmlout = "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
  
  # Pridanie korenoveho elementu
  if root_element != "":
    xmlout = xmlout + "<" + root_element + ">"
  
  # Pre vysledku dotazu na XML
  for s in sel:
    xmlout += sel[s].toxml()
  
  # Pridanie korenoveho elementu
  if root_element != "":
    xmlout = xmlout + "</" + root_element + ">"
  
  # Ak --output=... nie je zadany, vypisanie na stdout
  if output_filename == "":
    xmlout += '\n'
    sys.stdout.write(xmlout)
  
  # Ak --output=... je zadany, vypisanie do suboru
  else:
    try:
     o_file = open(output_filename, "w")
    except IOError:
      sys.stderr.write("xqr: output: cannot open file\n")
      sys.exit(OUTPUT_ERROR)
    
    xmlout += '\n'
    o_file.write(xmlout)
  
  sys.exit(E_SUCCESS)