'''
AnimeBot.py
Acts as the "main" file and ties all the other functionality together.
'''

import praw
from praw.handlers import MultiprocessHandler
from prawoauth2 import PrawOAuth2Server
import re
import traceback
import requests
import time

import Search
import CommentBuilder
import DatabaseHandler
import Config
import Reference

TIME_BETWEEN_PM_CHECKS = 60 #in seconds

try:
    import Config
    USERNAME = Config.username
    PASSWORD = Config.password
    USERAGENT = Config.useragent
    REDDITAPPID = Config.redditappid
    REDDITAPPSECRET = Config.redditappsecret
    REFRESHTOKEN = Config.refreshtoken
    SUBREDDITLIST = Config.get_formatted_subreddit_list()
except ImportError:
    pass

user_agent = 'Lewd/0.1'
reddit = praw.Reddit(user_agent=user_agent)
scopes = ['identity', 'read', 'submit', 'privatemessages']

oauthserver = PrawOAuth2Server(reddit, 'ETCyhisKnLla9w', 'jmYpEYiL85SSCBq-Gz47Zawhjto',
                               state=user_agent, scopes=scopes)
oauthserver.start()
#reddit = praw.Reddit('explainbot', user_agent = 'web:xkcd-explain-bot:v0.1 (by /u/Lewd)')
#reddit = praw.Reddit(client_id=REDDITAPPID,
#                     client_secret=REDDITAPPSECRET,
#                     redirect_uri='http://127.0.0.1:65010/',
#                     user_agent=USERAGENT)
#reddit = praw.Reddit(client_id=REDDITAPPID, client_secret=REDDITAPPSECRET,
#                     password=PASSWORD, user_agent=USERAGENT,
#                     username=USERNAME)

#reddit = praw.Reddit(client_id = 'ETCyhisKnLla9w',
#		     client_secret = 'jmYpEYiL85SSCBq-Gz47Zawhjto',
#                     username = 'lewd_roboragi',
#                     password = 'Bloodwork90&*',
#                     user_agent = 'Lewd/0.1')


#client_auth = requests.auth.HTTPBasicAuth('ETCyhisKnLla9w', 'jmYpEYiL85SSCBq-Gz47Zawhjto')
##post_data = {"grant_type": "password", "username": "lewd_roboragi", "password": "Bloodwork90&*"}
#post_data = {"state": "13eb9327-f40e-4ef1-8020-1c36af1b4b70", "scope": "identity", "client_id" : "ETCyhisKnLla9w", "redirect_uri" : "http://127.0.0.1", "code" : "6bUX_5tVxCoAy-KcA91M2jasKdE", "grant_type" : "password", "response_type" : "code"}
#headers = {"User-Agent": "Lewd/0.1"}
##response = requests.post("https://www.reddit.com/api/v1/access_token", auth = client_auth, data = post_data, headers = headers)
#response = requests.post("https://www.reddit.com/api/v1/access_token", auth = client_auth, data = post_data, headers = headers)
#access_response_data = response.json()
#print(access_response_data)
#REFRESHTOKEN = access_response_data['access_token']

#client_auth = requests.auth.HTTPBasicAuth('ETCyhisKnLla9w', 'jmYpEYiL85SSCBq-Gz47Zawhjto')
#headers = { 'user-agent': "Lewd/0.1" }
#post_data = { "grant_type": "password", "username" : "lewd_roboragi", "password": "Bloodwork90&*" }
#response = requests.post( "https://www.reddit.com/api/v1/access_token", auth = client_auth, data = post_data, headers = headers )
#token_data = response.json( )
#reddit.set_access_credentials( token_data[ 'scope' ], token_data[ 'access_token' ] )



#the subreddits where expanded requests are disabled
disableexpanded = ['animesuggest']

#subreddits I'm actively avoiding
exiled = ['anime']

#Sets up Reddit for PRAW
def setupReddit():
#    try:
    print('Setting up Reddit')
    reddit.set_oauth_app_info(client_id='ETCyhisKnLla9w', client_secret='jmYpEYiL85SSCBq-Gz47Zawhjto', redirect_uri='http://127.0.0.1:65010/authorize_callback')
    tokens = oauthserver.get_access_codes()
    print(tokens)
    reddit.refresh_access_information(tokens['refresh_token'])
    #url = reddit.get_authorize_url('uniqueKey', 'identity', True)
    #access_information = reddit.get_access_information('f4_hYd44ZOq3Sph_LND5ITOClek')
    #print(url)
#    reddit.refresh_access_information(access_response_data['access_token'])

#    submissions = reddit.get_subreddit('obscenegames').get_hot(limit=10)

#    for x in submissions:
#        print(x)

    print('Reddit successfully set up')
    #except Exception as e:
    #     print('Error with setting up Reddit: ' + str(e))

#function for processing edit requests via pm
def process_pms():
    for msg in reddit.get_unread(limit=None):
        if ((msg.subject == 'username mention') or (msg.subject == 'comment reply' and 'u/roboragi' in msg.body.lower())):
            if (('{' and '}') in msg.body) or (('<' and '>') in msg.body) or ((']' and '[') in msg.body):
                try:
                    if str(msg.subreddit).lower() in exiled:
                        #print('Edit request from exiled subreddit: ' + str(msg.subreddit) + '\n')
                        #msg.mark_as_read()
                        continue

                    mentionedComment = reddit.get_info(thing_id=msg.name)
                    mentionedComment.refresh()

                    replies = mentionedComment.replies

                    ownComments = []
                    commentToEdit = None

                    for reply in replies:
                        if (reply.author.name == 'Roboragi'):
                            ownComments.append(reply)

                    for comment in ownComments:
                        if 'http://www.reddit.com/r/Roboragi/wiki/index' in comment.body:
                            commentToEdit = comment

                    commentReply = process_comment(mentionedComment, True)

                    try:
                        if (commentReply):
                            if commentToEdit:
                                commentToEdit.edit(commentReply)
                                print('Comment edited.\n')
                            else:
                                mentionedComment.reply(commentReply)
                                print('Comment made.\n')
                            
                            msg.mark_as_read()
                            
                            if not (DatabaseHandler.commentExists(mentionedComment.id)):
                                DatabaseHandler.addComment(mentionedComment.id, mentionedComment.author.name, msg.subreddit, True)
                    except praw.errors.Forbidden:
                        print('Edit request from banned subreddit: ' + str(msg.subreddit) + '\n')

                except Exception as e:
                    print(e)

#process dat comment
def process_comment(comment, is_edit=False):
    #Anime/Manga requests that are found go into separate arrays
    animeArray = []
    mangaArray = []
    lnArray = []

    #ignores all "code" markup (i.e. anything between backticks)
    comment.body = re.sub(r"\`[{<\[]+(.*?)[}>\]]+\`", "", comment.body)

    num_so_far = 0
    
    #This checks for requests. First up we check all known tags for the !stats request
    if re.search('({!stats.*?}|{{!stats.*?}}|<!stats.*?>|<<!stats.*?>>)', comment.body, re.S) is not None:
        username = re.search('[uU]\/([A-Za-z0-9_-]+?)(>|}|$)', comment.body, re.S)
        subreddit = re.search('[rR]\/([A-Za-z0-9_]+?)(>|}|$)', comment.body, re.S)

        if username:
            commentReply = CommentBuilder.buildStatsComment(username=username.group(1))
        elif subreddit:
            commentReply = CommentBuilder.buildStatsComment(subreddit=subreddit.group(1))
        else:
            commentReply = CommentBuilder.buildStatsComment()
    else:
        
        #The basic algorithm here is:
        #If it's an expanded request, build a reply using the data in the braces, clear the arrays, add the reply to the relevant array and ignore everything else.
        #If it's a normal request, build a reply using the data in the braces, add the reply to the relevant array.

        #Counts the number of expanded results vs total results. If it's not just a single expanded result, they all get turned into normal requests.
        numOfRequest = 0
        numOfExpandedRequest = 0
        forceNormal = False

        for match in re.finditer("\{{2}([^}]*)\}{2}|\<{2}([^>]*)\>{2}", comment.body, re.S):
            numOfRequest += 1
            numOfExpandedRequest += 1
            
        for match in re.finditer("(?<=(?<!\{)\{)([^\{\}]*)(?=\}(?!\}))|(?<=(?<!\<)\<)([^\<\>]*)(?=\>(?!\>))", comment.body, re.S):
            numOfRequest += 1

        if (numOfExpandedRequest >= 1) and (numOfRequest > 1):
            forceNormal = True

        #The final comment reply. We add stuff to this progressively.
        commentReply = ''

        #if (numOfRequest + numOfExpandedRequest) > 25:
        #    commentReply = 'You have tried to request too many things at once. Please reduce the number of requests and try again.'
        #else:

        #Expanded Anime
        for match in re.finditer("\{{2}([^}]*)\}{2}", comment.body, re.S):
            if num_so_far < 30:
                reply = ''

                if (forceNormal) or (str(comment.subreddit).lower() in disableexpanded):
                    reply = Search.buildAnimeReply(match.group(1), False, comment)
                else:
                    reply = Search.buildAnimeReply(match.group(1), True, comment)                    

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    animeArray.append(reply)

        #Normal Anime  
        for match in re.finditer("(?<=(?<!\{)\{)([^\{\}]*)(?=\}(?!\}))", comment.body, re.S):
            if num_so_far < 30:
                reply = Search.buildAnimeReply(match.group(1), False, comment)
                
                if (reply is not None):
                    num_so_far = num_so_far + 1
                    animeArray.append(reply)

        #Expanded Manga
        #NORMAL EXPANDED
        for match in re.finditer("\<{2}([^>]*)\>{2}(?!(:|\>))", comment.body, re.S):
            if num_so_far < 30:
                reply = ''
                
                if (forceNormal) or (str(comment.subreddit).lower() in disableexpanded):
                    reply = Search.buildMangaReply(match.group(1), False, comment)
                else:
                    reply = Search.buildMangaReply(match.group(1), True, comment)

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    mangaArray.append(reply)

        #AUTHOR SEARCH EXPANDED
        for match in re.finditer("\<{2}([^>]*)\>{2}:\(([^)]+)\)", comment.body, re.S):
            if num_so_far < 30:
                reply = ''
                
                if (forceNormal) or (str(comment.subreddit).lower() in disableexpanded):
                    reply = Search.buildMangaReplyWithAuthor(match.group(1), match.group(2), False, comment)
                else:
                    reply = Search.buildMangaReplyWithAuthor(match.group(1), match.group(2), True, comment)

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    mangaArray.append(reply)

        #Normal Manga
        #NORMAL
        for match in re.finditer("(?<=(?<!\<)\<)([^\<\>]+)\>(?!(:|\>))", comment.body, re.S):
            if num_so_far < 30:
                reply = Search.buildMangaReply(match.group(1), False, comment)

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    mangaArray.append(reply)

        #AUTHOR SEARCH
        for match in re.finditer("(?<=(?<!\<)\<)([^\<\>]*)\>:\(([^)]+)\)", comment.body, re.S):
            if num_so_far < 30:
                reply = Search.buildMangaReplyWithAuthor(match.group(1), match.group(2), False, comment)

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    mangaArray.append(reply)

        #Expanded LN
        for match in re.finditer("\]{2}([^]]*)\[{2}", comment.body, re.S):
            if num_so_far < 30:
                reply = ''

                if (forceNormal) or (str(comment.subreddit).lower() in disableexpanded):
                    reply = Search.buildLightNovelReply(match.group(1), False, comment)
                else:
                    reply = Search.buildLightNovelReply(match.group(1), True, comment)                    

                if (reply is not None):
                    num_so_far = num_so_far + 1
                    lnArray.append(reply)

        #Normal LN  
        for match in re.finditer("(?<=(?<!\])\](?!\())([^\]\[]*)(?=\[(?!\[))", comment.body, re.S):
            if num_so_far < 30:
                reply = Search.buildLightNovelReply(match.group(1), False, comment)
                
                if (reply is not None):
                    num_so_far = num_so_far + 1
                    lnArray.append(reply)
        
        #Here is where we create the final reply to be posted

        #Basically just to keep track of people posting the same title multiple times (e.g. {Nisekoi}{Nisekoi}{Nisekoi})
        postedAnimeTitles = []
        postedMangaTitles = []
        postedLNTitles = []

        #Adding all the anime to the final comment. If there's manga too we split up all the paragraphs and indent them in Reddit markup by adding a '>', then recombine them
        for i, animeReply in enumerate(animeArray):
            if not (i is 0):
                commentReply += '\n\n'

            if not (animeReply['title'] in postedAnimeTitles):
                postedAnimeTitles.append(animeReply['title'])
                commentReply += animeReply['comment']
            

        if mangaArray:
            commentReply += '\n\n'

        #Adding all the manga to the final comment
        for i, mangaReply in enumerate(mangaArray):
            if not (i is 0):
                commentReply += '\n\n'
            
            if not (mangaReply['title'] in postedMangaTitles):
                postedMangaTitles.append(mangaReply['title'])
                commentReply += mangaReply['comment']

        if lnArray:
            commentReply += '\n\n'

        #Adding all the manga to the final comment
        for i, lnReply in enumerate(lnArray):
            if not (i is 0):
                commentReply += '\n\n'
            
            if not (lnReply['title'] in postedLNTitles):
                postedLNTitles.append(lnReply['title'])
                commentReply += lnReply['comment']

        #If there are more than 10 requests, shorten them all 
        if not (commentReply is '') and (len(animeArray) + len(mangaArray)+ len(lnArray) >= 10):
            commentReply = re.sub(r"\^\((.*?)\)", "", commentReply, flags=re.M)

    #If there was actually something found, add the signature and post the comment to Reddit. Then, add the comment to the "already seen" database.
    if commentReply is not '':
        '''if (comment.author.name == 'treborabc'):
            commentReply = '[No.](https://www.reddit.com/r/anime_irl/comments/4sba1n/anime_irl/d58xkha)'''
        
        if num_so_far >= 30:
            commentReply += "\n\nI'm limited to 30 requests at once and have had to cut off some, sorry for the inconvinience!\n\n"

        #commentReply += Config.getSignature(comment.permalink)
        #commentReply += comment.permalink

        commentReply += Reference.get_bling(comment.author.name)

        if is_edit:
            return commentReply
        else:
            try:
                comment.reply(commentReply)
                print("Comment made.\n")
            except praw.errors.Forbidden:
                print('Request from banned subreddit: ' + str(comment.subreddit) + '\n')
            except Exception:
                traceback.print_exc()

            comment_author = comment.author.name if comment.author else '!UNKNOWN!'
            
            try:
                DatabaseHandler.addComment(comment.id, comment_author, comment.subreddit, True)
            except:
                traceback.print_exc()
    else:
        try:
            if is_edit:
                return None
            else:
                comment_author = comment.author.name if comment.author else '!UNKNOWN!'
                
                DatabaseHandler.addComment(comment.id, comment_author, comment.subreddit, False)
        except:
            traceback.print_exc()
    

#The main function
def start():
    last_checked_pms = time.time()

    #This opens a constant stream of comments. It will loop until there's a major error (usually this means the Reddit access token needs refreshing)
    comment_stream = praw.helpers.comment_stream(reddit, reddit.get_subreddit('obscenegames'), limit=50, verbosity=0)
    #print(comment_stream)
    for comment in comment_stream:
        #print(comment)
        # check if it's time to check the PMs
        if (time.time() - last_checked_pms) > TIME_BETWEEN_PM_CHECKS:
            process_pms()
            last_checked_pms = time.time()

        #Is the comment valid (i.e. it's not made by Roboragi and I haven't seen it already). If no, try to add it to the "already seen pile" and skip to the next comment. If yes, keep going.
        if not (Search.isValidComment(comment, reddit)):
            try:
                if not (DatabaseHandler.commentExists(comment.id)):
                    DatabaseHandler.addComment(comment.id, comment.author.name, comment.subreddit, False)
            except:
                pass
            continue

        process_comment(comment)


# ------------------------------------#
#Here's the stuff that actually gets run

#Initialise Reddit.
setupReddit()

#Loop the comment stream until the Reddit access token expires. Then get a new access token and start the stream again.
while 1:
    try:        
        start()
    except Exception as e:
        traceback.print_exc()
        pass
