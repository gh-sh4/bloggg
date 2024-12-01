# bloggg
This is a tool for generating `sh4.dev` (or any other site!) based on markdown files and a couple of templates. Why not use hugo/ghost/etc? They all seemed a bit more complex and harder to understand or add a feature compared to just having a <200 line python script. This does exactly what I want, I understand it, and it's easy to tinker with. Maybe it's useful for you too 😊

```
# Install stuff via venv or globally: 
pip install mistletoe yaml watchdog
python mds.py -i <input dir> -o <output dir> [-w]
```

You can optionally install `pip install watchdog` and enable watch mode (`-w`) in order to get bloggg to run against files as soon as they are modified.

Bloggg? It's not just for blogs, but I like the name.

## File structure / How does it work?
- bloggg transforms all markdown files in the input directory into html files in the output directory. Directory structures are mirrored into the output directory.
- All CSS, images, and JS files are copied directly from their locations in the input directory to the output directory.
- The input directory should contain a `_templates` folder for html templates. The template folder should contain one html file per template, and the name before '.html' will be used to match which `template:` in the frontmatter of markdown files in order to determine which template to use. 
    - All other css/js/images from the _templates folder will be copied into `_template` in the output directory, and generated html files will have src/href's re-written to point to those assets in the output _template directory.

## Built-in substitutions
- **`$$BREADCRUMBS$$`** will be replaced with a unix path-like list of links from your site root to the current page, assuming every page exists as an `index.md` in a folder for its own page.
- **`$$DOC_TITLE$$`** will be replaced with the `title:` from the markdown frontmatter. 
- **`$$DOC_CONTENT$$`** will be replaced with the rendered markdown html.
- **`$$DOC_DATE$$`** will be replaced with the `date:` from the markdown frontmatter. 
