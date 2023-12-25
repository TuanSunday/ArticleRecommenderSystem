import numpy as np
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth, association_rules

event_type_strength = {
   'VIEW': 1.0,
   'LIKE': 2.0, 
   'BOOKMARK': 2.5, 
   'FOLLOW': 3.0,
   'COMMENT CREATED': 4.0,  
}

class AprioriRecommender:
    
    MODEL_NAME = 'Apriori'
    
    def __init__(self, articles_df= None, interactions_df= None, event_type_strength = None):
        self.interactions_df = interactions_df
        self.event_type_strength = event_type_strength
        self.interactions_df['eventStrength'] = interactions_df['eventType'].apply(lambda x: event_type_strength[x])
        users_interactions_count_df = self.interactions_df.groupby(['personId', 'contentId']).size().groupby('personId').size()
        users_with_enough_interactions_df = users_interactions_count_df[users_interactions_count_df >= 5].reset_index()[['personId']]
        interactions_from_selected_users_df = self.interactions_df.merge(users_with_enough_interactions_df, 
                how = 'right',
                left_on = 'personId',
                right_on = 'personId')
        
        # self.interactions_full_df = interactions_from_selected_users_df \
        #                 .groupby(['personId', 'contentId'])['eventStrength'].sum() \
        #                 .apply(self.smooth_user_preference).reset_index()
        
        self.items_df = articles_df
        dataset = list(interactions_from_selected_users_df.groupby('personId', as_index=False).agg({'contentId': list})['contentId'].values)
        te = TransactionEncoder()
        te_ary = te.fit(dataset).transform(dataset)
        df = pd.DataFrame(te_ary, columns=te.columns_)
        res = association_rules(fpgrowth(df, min_support=0.005, use_colnames=True, max_len=2), metric="lift", min_threshold=1).sort_values('lift', ascending=False)
        res['antecedents'] = [list(i)[0] for i in res['antecedents']]
        res['consequents'] = [list(i)[0] for i in res['consequents']]

        self.rules_df = res

    def get_model_name(self):
        return self.MODEL_NAME
        
    def _get_similar_items_to_user_profile(self, person_id):
        cands = list(self.interactions_df.loc[self.interactions_df['personId'] == person_id, 'contentId'].values)
        
        cands = self.interactions_df.loc[self.interactions_df['personId'] == person_id, ['contentId', 'eventStrength']]
        # self.rules_df['consequents'] = self.rules_df['consequents'].astype('int64')
        cands = cands.merge(self.rules_df, right_on='antecedents', left_on='contentId', how='inner')

        cands['lift'] = np.log(cands['lift'] * cands['eventStrength'])
        # cands['contentId'] = cands['contentId'].astype('int64')
        ###bug
        selected_cands = cands[['consequents', 'lift']].sort_values('lift', ascending=False)
        return selected_cands
    
    def get_items_interacted(self, person_id, interactions_df):
        # Get the user's data and merge in the movie information.
        interacted_items = interactions_df.loc[person_id]['contentId']
        return set(interacted_items if type(interacted_items) == pd.Series else [interacted_items])
    
    def update_interactions_df(self, interactions_df):
            # Get the user's data and merge in the movie information.
        self.interactions_df = interactions_df
        return self.interactions_df
    
    def update_user_profile(self, person_id = None):
            # Get the user's data and merge in the movie information.
        if person_id is not None:
            self.interactions_df.loc[self.interactions_df['personId'] == person_id, 'eventStrength'] = self.interactions_df\
                                                                                                    .loc[self.interactions_df['personId'] \
                                                                                                    == person_id,'eventType'].apply(lambda x: \
                                                                                                     self.event_type_strength[x])
        return self.interactions_df
        
    def recommend_items(self, user_id, ignore_interacted= False, topn=10, verbose= False):
        similar_items = self._get_similar_items_to_user_profile(user_id)
        items_to_ignore = self.get_items_interacted(user_id, self.interactions_df.set_index('personId'))
        if ignore_interacted == True:
            similar_items_filtered = similar_items.loc[~similar_items['consequents'].isin(items_to_ignore),:]
        else:
            similar_items_filtered = similar_items
        similar_items_filtered.columns=['contentId', 'recStrength']
        recommendations_df = similar_items_filtered.head(topn)
        if verbose:
            if self.items_df is None:
                raise Exception('"items_df" is required in verbose mode')
            
            recommendations_df = recommendations_df.merge(self.items_df, how = 'left', 
                                                        left_on = 'contentId', 
                                                        right_on = 'contentId')[['recStrength', 'contentId', 'title', 'url', 'lang']]
        recommendations_df.drop_duplicates(subset= 'contentId', keep= 'first',inplace=True)

        return recommendations_df

if __name__ == "__main__":
    pd.options.display.float_format = '{:.0f}'.format
    articles_df = pd.read_csv('data/shared_articles.csv')
    articles_df = articles_df[articles_df['eventType'] == 'CONTENT SHARED']
    interactions_df = pd.read_csv('data/users_interactions.csv')
    person_id = -9150583489352258206 #-9150583489352258206 #-1479311724257856983

    apriori_recommender_model = AprioriRecommender(articles_df, interactions_df, event_type_strength)
    result = apriori_recommender_model.recommend_items(user_id= person_id, ignore_interacted=True, topn=10, verbose= True)
    print(result)