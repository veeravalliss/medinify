"""
Examples for how to use the Medinify package
"""

from medinify.sentiment.review_classifier import ReviewClassifier

""" Naive bayes classifier
"""

def main():
    """ Main function.
    """
    review_classifier = ReviewClassifier('nb', 'stopwords.txt')
    review_classifier.train('citalopram_train.csv')
    review_classifier.classify('neutral.txt')

if __name__ == "__main__":
    main()

""" Decision tree classifier
"""

def main():
    """ Main function.
    """
    review_classifier = ReviewClassifier('dt', 'stopwords.txt')
    review_classifier.train('citalopram_train.csv')
    review_classifier.classify('neutral.txt')

if __name__ == "__main__":
    main()
