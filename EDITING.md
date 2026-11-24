# How to edit the More Than a Meal website

You don't need to know how to code. Every page is a plain file you can edit right on github.com. When you save ("commit") a change, Vercel rebuilds the site and it's live in about 30 seconds.

## Which file is which page

| Page | File |
|---|---|
| Home | `index.html` |
| Our story | `story.html` |
| Classes | `classes.html` |
| Meet the teachers | `teachers.html` |
| Farm partners | `farms.html` |
| Book a class (the form) | `book.html` |
| Thank-you page after booking | `thanks.html` |
| Photos | the `images` folder |
| Colors and fonts | `css/style.css` (you shouldn't need to touch this) |

## Edit text

1. Go to the site's repository on github.com and click the file for the page (for example `classes.html`).
2. Click the **pencil icon** (top right of the file, "Edit this file").
3. Find the words you want to change. Press Ctrl+F (Cmd+F on a Mac) to search for them.
4. Change only the words between the tags. For example, in `<p class="card__text">Serves 4 and doubles easily.</p>`, change the words but leave `<p class="card__text">` and `</p>` alone.
5. Click **Commit changes...** (green button), type a short note like "Fix chili description", and click **Commit changes** again.
6. Wait about 30 seconds and refresh the live site.

If something looks broken afterwards, open the file's **History**, look at what changed, and put it back the way it was. Nothing is ever lost.

## Swap a photo

**Easiest way (same name):**
1. Name your new photo exactly the same as the old one (for example `teacher-maddie.jpg`).
2. Open the `images` folder on github.com, click **Add file > Upload files**, drag the photo in, and commit. It replaces the old one.

**New name:**
1. Upload the photo to the `images` folder (Add file > Upload files, then commit).
2. Open the page file, search for the old photo name (for example `lemon-chicken-orzo.jpg`), and change it to the new name in `src="images/..."`.
3. Also update `alt="..."` (a short description of the photo, read aloud for blind visitors), and `width="..."` and `height="..."` to the new photo's size in pixels (a rough match is fine; it just stops the page jumping while it loads).

Tips: keep photos under about 1200 pixels wide and use `.jpg`. Avoid spaces and capital letters in file names (use `hot-honey-shrimp.jpg`, not `Hot Honey Shrimp.JPG`).

## Add a class, teacher or farm

Each card has a comment above it that looks like this:

```
<!-- CLASS CARD: copy this whole block ... -->
<article class="card card--class">
  ...
</article>
<!-- END CLASS CARD -->
```

1. Open the page (`classes.html`, `teachers.html` or `farms.html`) and click the pencil icon.
2. Select everything from the `<!-- CLASS CARD` line down to `<!-- END CLASS CARD -->`, copy it, and paste it right after the `END` line.
3. Change the name, description and other text in your copy.
4. Commit.

Extra steps:
- **New class:** also open `book.html`, find the "Which recipe?" list, and add a line like `<option>Chicken Stir Fry</option>` with the name spelled **exactly** as on the card. The card's "Book this class" link ends in `book.html?class=` plus the name with spaces written as `%20` (for example `book.html?class=Chicken%20Stir%20Fry`). That's what pre-selects the recipe on the form.
- **No photo yet?** Class and farm cards can use a colored panel instead of a photo:
  `<div class="card__img card__img--panel" aria-hidden="true"><span class="card__panel-label">Dish name</span></div>`.
  Add `card__img--tomato`, `card__img--butter` or `card__img--herb` after `card__img--panel` for a different color. When you get a photo, replace that whole line with an `<img class="card__img" src="images/your-photo.jpg" alt="..." width="1200" height="900" loading="lazy">` line.
- **Teacher without a "Loves to cook" line:** just delete the `<p class="card__loves">...</p>` line from the copy.

To remove a card, delete everything from its `<!--` comment line to its `END` line.

## Change the booking email

When someone taps "Send request", their email app opens with a message to the booking address, already filled in with everything they typed. They hit send and it lands in that inbox. No outside service, nothing to activate.

1. Open `book.html` and click the pencil icon.
2. Find `data-email="aff3ua@virginia.edu"` and change the address.
3. Commit.

You may also want to change the email shown in the text and footer: search each page for `aff3ua@virginia.edu` and replace it (it appears on every page in the footer).

## Change the price

The price appears in several places. On github.com, open each page and search for `$14`:
- `classes.html` (the line under the intro, and once on every class card)
- `book.html` (under the intro)
- `index.html` (the round sticker on the photo, and the Classes teaser)
- the footer and the phone "Book a class" bar on every page (`$14 per person · groups of 6+`)

Also update the short page descriptions near the top of `classes.html` and `book.html` (the line that starts `<meta name="description"`), which mention $14.

## Change the Instagram link

The Instagram link is in the footer of every page. Note: `@morethanameal.uva` is a stand-in until the real account is confirmed.

1. Open each page file and search for `instagram.com`.
2. Change the link in `href="https://www.instagram.com/morethanameal.uva/"` to the new account.
3. Change the handle text `@morethanameal.uva` right below it.
4. Commit. Repeat for every `.html` file (there are 7).
