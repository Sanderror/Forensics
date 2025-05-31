from bs4 import BeautifulSoup
import os
import pandas as pd
import pickle

# Load HTML file content from disk
def load_file(path):
    with open(path, 'r') as f:
        content = f.read()
    return content

# Parse HTML and extract post + comments into message_list
def scraper(message_list, content):
    soup = BeautifulSoup(content, 'html.parser')

    # Extract main post details
    post = soup.find("div", class_="content no-top")
    title = post.find("a", class_="title").text.strip()
    message = post.find("div", class_="postContent").text.strip()
    time = post.find("div", class_="author").find("span")["title"]
    message_id = post.find("form", class_="actions").find("a")["href"]
    user = post.find("div", class_="author").find("a")["href"]
    subdread = post.find("div", class_="subBanner").find("a")["href"]
    nr_of_comments = post.find("form", class_="actions").find("a").text.split()[0]
    comment_bin = False  # Indicates this is the main post, not a comment

    # Add main post to message list
    orig_message = [message, message_id, title, user, time, subdread, nr_of_comments, comment_bin]
    message_list.append(orig_message)

    # Extract all comments under the post
    comment_section = soup.find_all("div", class_="comment")
    for comment in comment_section:
        comment_text = comment.find("div", class_="commentBody").text.strip()
        comment_user = comment.find("div", class_="top").find("a", class_="username")["href"]
        comment_time = comment.find("div", class_="timestamp").find("span")["title"]
        comment_bin = True  # Mark as comment

        # Add comment to message list
        comment_temp = [comment_text, message_id, title, comment_user, comment_time, subdread, 8, comment_bin]
        message_list.append(comment_temp)

    return message_list

if __name__ == '__main__':
    page_messages = []  # Store all post and comment data
    webpages_root = 'webpages'  # Root folder with all subdread folders

    # Loop through all subdirectories in 'webpages'
    for subdread in os.listdir(webpages_root):
        folder_path = os.path.join(webpages_root, subdread)

        # Make sure it's a directory
        if os.path.isdir(folder_path):
            for path in os.listdir(folder_path):
                if path.endswith('.html'):
                    full_path = os.path.join(folder_path, path)

                    # Skip home (index) pages
                    if 'home' not in full_path:
                        print('Scrape normal:', full_path)
                        content = load_file(full_path)

                        # Try to parse and extract data, handle errors gracefully
                        try:
                            page_messages = scraper(page_messages, content)
                        except Exception as e:
                            print(f"Error processing item {full_path}: {e}")
                            continue

    print('Process completed')
    print(f'Dataset contains {len(page_messages)} messages')

    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(page_messages, columns=[
        'Message', 'MessageId', 'MessageTitle',
        'User', 'Timestamp', 'Subdread', 'NumberOfComments', 'CommentTof'
    ])
    df.to_csv(path_or_buf=f'drugs_data.csv', index=False)
