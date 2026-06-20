#!/usr/bin/env python3
import argparse
import json
import os
import re

from yaml import load
try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader


def ensure_dir(dirname: str):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def load_highlight_groups(*syntax_yamls):
    highlight_groups = {}
    for y in syntax_yamls:
        try:
            with open(y, 'r') as h:
                config = load(h, Loader=Loader) or {}
        except FileNotFoundError:
            print(f"{y} not found, skip")
            continue
        if not isinstance(config, dict):
            raise ValueError(f"{y} must contain a YAML mapping at top level")
        highlight_groups.update(config)
    return highlight_groups


def normalize_tag(tag):
    if isinstance(tag, str):
        return {"name": tag}
    if not isinstance(tag, dict):
        raise TypeError(f"Tag entries must be strings or mappings, got {tag!r}")

    if "name" in tag:
        normalized = dict(tag)
    elif "word" in tag:
        normalized = dict(tag)
        normalized["name"] = normalized["word"]
    elif len(tag) == 1:
        name, metadata = next(iter(tag.items()))
        normalized = {"name": name}
        if isinstance(metadata, dict):
            normalized.update(metadata)
        elif metadata is not None:
            normalized["info"] = metadata
    else:
        raise ValueError(f"Tag mapping must contain a 'name' key: {tag!r}")

    normalized["name"] = str(normalized["name"])
    return normalized


def normalize_tags(config):
    return [normalize_tag(tag) for tag in config.get("tags", [])]


def completion_module_name(filetype: str):
    module = "{}complete".format(re.sub(r"[^0-9A-Za-z_]", "_", filetype))
    if module[0].isdigit():
        module = "x_{}".format(module)
    return module


def completion_contexts(config):
    complete_after = config.get("complete_after")
    if isinstance(complete_after, str):
        return [complete_after]
    if isinstance(complete_after, list):
        return [str(item) for item in complete_after]

    prefix = config.get("prefix")
    if not isinstance(prefix, str):
        return []

    match = re.match(r"^([A-Za-z_][0-9A-Za-z_]*)\\s\\\+$", prefix)
    if match:
        return [match.group(1)]
    return []


def make_completion_item(tag, group_name: str, context: str = ""):
    item = {"word": tag["name"]}

    kind = str(tag.get("kind", "k"))
    if kind:
        item["kind"] = kind[0]

    if "abbr" in tag:
        item["abbr"] = str(tag["abbr"])

    if "menu" in tag:
        item["menu"] = str(tag["menu"])
    elif "args" in tag:
        item["menu"] = str(tag["args"])
    elif context:
        item["menu"] = context
    else:
        item["menu"] = group_name

    if "info" in tag:
        item["info"] = str(tag["info"])
    elif "args" in tag:
        item["info"] = "{} {}".format(tag["name"], tag["args"])

    return item


def add_completion_item(items, seen, item):
    word = item["word"]
    if word in seen:
        return
    seen.add(word)
    items.append(item)


def generate_ftdetect(d, filetype: str, force: bool = False):
    dirname = os.path.join(d, "ftdetect")
    ensure_dir(dirname)
    fn = os.path.join(dirname, "{}.vim".format(filetype))
    if os.path.exists(fn) and not force:
        print("{} exists. Skip".format(fn))
        return

    with open(fn, 'w') as h:
        print("\" This file is generated automatically. Manual edit might be lost", file=h)
        print(r"""augroup filetype_{filetype}
  autocmd!
  autocmd BufNewFile,BufRead librpa.in set filetype={filetype}
augroup END""".format(filetype=filetype), file=h)


def generate_ftplugin(d, filetype: str, force: bool = False):
    dirname = os.path.join(d, "ftplugin")
    ensure_dir(dirname)
    fn = os.path.join(dirname, "{}.vim".format(filetype))
    if os.path.exists(fn) and not force:
        print("{} exists. Skip".format(fn))
        return

    completion_module = completion_module_name(filetype)
    with open(fn, 'w') as h:
        print("\" This file is generated automatically. Manual edit might be lost", file=h)
        print("""set syntax={filetype}
setlocal comments=:#
setlocal commentstring=#%s
setlocal omnifunc={completion_module}#Complete""".format(
            filetype=filetype,
            completion_module=completion_module,
        ), file=h)


def generate_syntax(d, filetype: str, force: bool = False, *syntax_yamls):
    dirname = os.path.join(d, "syntax")
    ensure_dir(dirname)
    fn = os.path.join(dirname, "{}.vim".format(filetype))
    if os.path.exists(fn) and not force:
        print("{} exists. Skip".format(fn))
        return

    highlight_groups = load_highlight_groups(*syntax_yamls)

    with open(fn, 'w') as h:
        def p(*args):
            print(*args, file=h)

        p("\" This file is generated automatically. Manual edit might be lost")
        p("syn match librpaComment\t\"#.*$\"")
        p("hi def link librpaComment\tComment")
        p()
        for name, config in highlight_groups.items():
            group = config["group"]
            tags = normalize_tags(config)

            match_strs = []
            if len(tags) > 0:
                tag_names = [tag["name"] for tag in tags]
                match_str = "\\v<({})>".format("|".join(tag_names))
                if "prefix" in config:
                    match_str = config["prefix"] + match_str
                match_strs.append(match_str)
            if "extras" in config:
                match_strs.extend(config["extras"])
            for s in match_strs:
                p("syn match librpa{}\t\"^\\s*{}\"".format(name, s))
            if len(match_strs) > 0:
                p("hi def link librpa{}\t{}".format(name, group))
                p()


def generate_completion(d, filetype: str, force: bool = False, *syntax_yamls):
    dirname = os.path.join(d, "autoload")
    ensure_dir(dirname)
    completion_module = completion_module_name(filetype)
    fn = os.path.join(dirname, "{}.vim".format(completion_module))
    if os.path.exists(fn) and not force:
        print("{} exists. Skip".format(fn))
        return

    highlight_groups = load_highlight_groups(*syntax_yamls)
    top_level_items = []
    top_level_seen = set()
    context_items = {}

    for group_name, config in highlight_groups.items():
        if config.get("complete", True) is False:
            continue

        tags = [
            tag for tag in normalize_tags(config)
            if tag.get("complete", True) is not False
        ]
        contexts = completion_contexts(config)

        if contexts:
            for context in contexts:
                add_completion_item(
                    top_level_items,
                    top_level_seen,
                    {
                        "word": context,
                        "kind": "k",
                        "menu": group_name,
                    },
                )

                items = context_items.setdefault(context, [])
                seen = {item["word"] for item in items}
                for tag in tags:
                    add_completion_item(
                        items,
                        seen,
                        make_completion_item(tag, group_name, context),
                    )
            continue

        for tag in tags:
            add_completion_item(
                top_level_items,
                top_level_seen,
                make_completion_item(tag, group_name),
            )

    with open(fn, 'w') as h:
        def p(*args):
            print(*args, file=h)

        p("\" This file is generated automatically. Manual edit might be lost")
        p("let s:top_level_items = {}".format(json.dumps(top_level_items)))
        p("let s:context_items = {}".format(json.dumps(context_items)))
        p()
        p("""function! s:MatchesBase(item, base) abort
  return a:base ==# '' || a:item.word =~? '^' . escape(a:base, '\\.^$~[]')
endfunction

function! {completion_module}#Complete(findstart, base) abort
  if a:findstart
    let l:line = getline('.')
    let l:start = col('.') - 1
    while l:start > 0 && l:line[l:start - 1] =~# '\\k'
      let l:start -= 1
    endwhile
    return l:start
  endif

  let l:prefix = strpart(getline('.'), 0, col('.') - 1)
  if l:prefix =~# '#'
    return []
  endif

  let l:before_base = strpart(l:prefix, 0, strlen(l:prefix) - strlen(a:base))
  let l:context_words = split(l:before_base)
  let l:items = s:top_level_items
  if len(l:context_words) > 0 && has_key(s:context_items, l:context_words[0])
    let l:items = s:context_items[l:context_words[0]]
  endif

  return filter(copy(l:items), 's:MatchesBase(v:val, a:base)')
endfunction""".format(completion_module=completion_module))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-c", "--extra-configs", type=str,
                   default=[], nargs="+",
                   help="Additional YAML files to configure Vim syntax")
    p.add_argument("--ft", "--filetype", dest="filetype", type=str, default="librpain",
                   help="Filetype for LibRPA inputs in Vim, default: librpain")
    p.add_argument("-d", dest="directory", type=str, default=".",
                   help="Vim configuration directory, default: pwd")
    p.add_argument("-f", dest="force", action="store_true",
                   help="Force overwrite")
    args = p.parse_args()

    generate_ftdetect(args.directory, args.filetype, args.force)
    generate_ftplugin(args.directory, args.filetype, args.force)
    generate_completion(args.directory, args.filetype, args.force, "syntax.yml", *(args.extra_configs))
    generate_syntax(args.directory, args.filetype, args.force, "syntax.yml", *(args.extra_configs))
