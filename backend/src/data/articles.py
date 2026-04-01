class Articles:
    def __init__(self,publich_date,authors,type,title,text,keywords,summary,article_url):
        self.publish_date = publich_date
        self.authors = authors
        self.type = type
        self.title = title
        self.text = text
        self.summary = summary
        self.article_url = article_url
    @property
    def getPublishDate(self):
        return self.publish_date
    @property
    def getAuthors(self):
        return self.authors
    @property
    def getText(self):
        return self.text
    
    @property
    def getTitle(self):
        return self.title
    @property
    def getType(self):
        return self.type
    @property
    def getKeyWords(self):
        return self.keywords
    @property
    def getSummary(self):
        return self.summary
    @property
    def getArticleUrl(self):
        return self.article_url
    
    @getPublishDate.setter
    def getPublishDate(self,publish_date):
        self.publish_date = publish_date

    @getAuthors.setter
    def setAuthor(self,authors):
        self.authors = authors
    
    @getType.setter
    def setType(self,type):
        self.type = type

    @getText.setter
    def setText(self,text):
        self.text = text

    @getTitle.setter
    def setTitle(self,title):
        self.title = title

    @getKeyWords.setter
    def setKeyWords(self,keywords):
        self.keywords = keywords

    @getSummary.setter
    def setSummary(self,summary):
        self.summary = summary

    @getArticleUrl.setter
    def setArticleUrl(self,article_url):
        self.article_url = article_url