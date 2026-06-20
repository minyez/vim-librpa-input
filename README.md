# Vim extension for LibRPA input files

Filetype detection, syntax highlighting, and keyword completion for
[LibRPA](https://srlive1201.github.io/LibRPA) input file, `librpa.in`.
This is useful for quick check of invalid or deprecated keywords.
It uses the same generation framework as [vim-aims-input](https://github.com/minyez/vim-aims-input).

The keywords list is usually aligned with the master branch.

## Prerequisites

- Python 3
- [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)

## Usage

1. Clone this repository to vim configuration repository, e.g. "~/.vim/after"
2. Run

   ```shell
   python3 generate.py
   ```

3. By default it will create 4 files (also create directory when necessary)
   - `autoload/librpaincomplete.vim`
   - `ftdetect/librpain.vim`
   - `ftplugin/librpain.vim`
   - `syntax/librpain.vim`

   The file name `librpa` can be changed by option `--filetype` of `generate.py`
   Use `-f` to refresh existing generated files after upgrading this repository.

## Example use

Assume the prerequisites are satisfied.

Vim
```shell
mkdir -p ~/.vim/after
cd ~/.vim/after
git clone https://github.com/minyez/vim-librpa-input
cd vim-librpa-input
python3 generate.py -d ..
```

NeoVim
```shell
mkdir -p ~/.config/nvim/after
cd ~/.config/nvim/after
git clone https://github.com/minyez/vim-librpa-input
cd vim-librpa-input
python3 generate.py -d ..
```

## Configuration and extension

To add more keywords, you can create a custom configuration file, for example `custom.yml`.
The basic syntax is
```yaml
[SyntaxName]:
  group: [VimHlg]
  prefix: "prefix\\s\\+"
  tags:
  - tag1
  - tag2
```
This will highlight the combined keywords `prefix tag1` and `prefix   tag2` using the Vim highlight
group `VimHlg`. `custom.yml` can be parsed via the `-c`/`--extra-configs` flag

```shell
python3 generate.py -c custom.yml
```

The generated ftplugin sets Vim's `omnifunc`, so completion is available with `CTRL-X CTRL-O`
in insert mode. Completion is context-aware for prefixed groups: after `output `, only `output`
keywords are suggested.

Neovim completion plugins can use the same interface if they enable their omni/omnifunc source.
For example, with LazyVim's default `blink.cmp` setup:

```lua
{
  "saghen/blink.cmp",
  opts = {
    sources = {
      per_filetype = {
        librpain = { inherit_defaults = true, "omni" },
      },
    },
  },
}
```

After this, the regular Neovim completion menu can show the generated LibRPA candidates.

The syntax groups in `syntax.yml` can serve as examples.

Tag entries can be plain strings, as above, or mappings with completion metadata:

```yaml
General:
  group: Identifier
  tags:
  - name: nfreq
    info: "Number of frequency points."
```

The supported tag metadata fields are:

- `name`: the keyword inserted by completion and used for syntax highlighting
- `args`: short argument text shown in the completion menu
- `menu`: custom completion menu text, overriding `args` or the group name
- `info`: longer completion help text
- `kind`: one-character Vim completion kind, default `k`
- `complete`: set to `false` to keep the tag highlighted but omit it from completion

For prefixed groups, completion context is inferred from simple prefixes like
`"output\\s\\+"`. If a prefix is more complex, add `complete_after`:

```yaml
MyOutputGroup:
  group: Identifier
  prefix: "my_output\\s\\+"
  complete_after: my_output
  tags:
  - density
```

Please note that if multiple `SyntaxName` of syntax groups are found, only the last one parsed will be used.
