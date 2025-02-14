from flask import Flask, render_template, request, redirect, session, flash
import json
import os
import random
from pymongo import MongoClient, errors
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length
import hashlib

# Starting Flask with socketio
app = Flask(__name__,
            static_url_path='',
            static_folder='static',
            template_folder='templates');
app.config['SECRET_KEY'] = 'randomSecretKey'


# Connect to the database
# myclient = pymongo.MongoClient("mongodb://localhost:27017")

# Connecting to MongoDB
print("Connecting to database...")
try:
    myclient = MongoClient(
        host = "localhost:27017",
        serverSelectionTimeoutMS = 3000 # 3 second timeout
    )
    # print the version of MongoDB server if connection successful
    print ("server version:", myclient.server_info()["version"])
    # get the database_names from the MongoClient()
    database_names = myclient.list_database_names()
except errors.ServerSelectionTimeoutError as err:
    # set the client and DB name list to 'None' and `[]` if exception
    myclient = None
    database_names = []
    # catch pymongo.errors.ServerSelectionTimeoutError
    print ("pymongo ERROR:", err)
print ("\ndatabases:", database_names)
print("Connected to DB")

@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')

@app.route('/userHomepage')
def userHomepage():
    # print(session['user_id'])
    if session.get('user_id'):
        return render_template('userHomepage.html')
    return redirect('home')

# ORGANIZED BY CRUD OPERATION

# C(REATE) OPERATIONS
# Create a community, post a food item, register a user

class createCommunity(FlaskForm):
    """Start a new community!"""
    zipcode = StringField("Community's zipcode:", [DataRequired()])
    community = StringField('Name of your community:', [DataRequired()])
    submit = SubmitField('Register')

@app.route('/createCommunity', methods=('GET', 'POST'))
def create_community():
    form = createCommunity()
    return render_template('/createCommunity.html', form = form)

@app.route('/createCommunitySubmit', methods=('GET', 'POST'))
def create_community_submit():
    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        if (key == "zipcode"):
            zipcode = value
        elif (key == "community"):
            community = value

    print("Found community info:", zipcode, community)

    mydb = myclient["foodpool"]
    mycol = mydb["communities"]

    community_name = {
        'zipcode' : zipcode,
        'comm_name': community,
    }

    mycol.insert_one(community_name)
    return redirect('/home')

class postFood(FlaskForm):
    """Post a Food Item."""
    food_name = StringField('Name of Food', [DataRequired()])
    food_description = TextAreaField('Describe your food!')
    food_zipcode = StringField('Enter the zipcode of your food', [DataRequired()])
    food_price = StringField('Price', [DataRequired()])
    submit = SubmitField('Post')

@app.route('/postFood', methods=('GET', 'POST'))
def post_food():
    form = postFood()
    return render_template('/postFood.html', form = form)

@app.route('/postFoodSubmit', methods=('GET', 'POST'))
def post_food_submit():
    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        if (key == "food_name"):
            food_name = value
        elif (key == "food_description"):
            food_description = value
        elif (key == "food_price"):
            food_price = value
        elif (key == "food_zipcode"):
            food_zipcode = value

    print("Found food info:", food_name, food_description, food_price)

    mydb = myclient["foodpool"]
    mycol = mydb["posts"]

    post_id = genID(8)

    while post_id in [i['post_id'] for i in mycol.find()]:
        post_id = genID(8)

    donated = False

    post = {
        'post_id' : len([i for i in mycol.find()]) + 1,
        'food_name' : food_name,
        'food_descr': food_description,
        'food_price' : food_price,
        'food_zipcode' : food_zipcode,
        'user_id' : session['user_id'],
        'donated' : donated,
     }

    mycol.insert_one(post)
    return redirect('/userHomepage')


class registerUser(FlaskForm):
    """Register user form."""
    name = StringField('Name', [DataRequired()])
    user_name = StringField('Username', [DataRequired()])
    # verified = BooleanField('Are you verified?')
    zipcode = StringField('Zipcode', [DataRequired(), Length(min=5)])
    password = PasswordField('Password', [DataRequired()])
    submit = SubmitField('Register')

@app.route('/registerUser', methods=('GET', 'POST'))
def add_user():
    form = registerUser()
    return render_template('/registerUser.html', form = form)

@app.route('/registerUserSubmit', methods=('GET', 'POST'))
def add_user_submit():
    for key, value in request.form.items():
        # print("key: {0}, value: {1}".format(key, value))
        verified = "no"
        if (key == "name"):
            name = value
        elif (key == "user_name"):
            user_name = value
        elif (key == "verified"):
            if (value == 'y'):
                verified = "yes"
            # elif (value == 'n'):
            #     verified == "no"
        elif (key == "zipcode"):
            zipcode = value
        elif (key == "password"):
            password = hashlib.md5(value.encode()).hexdigest()
    print("Found user info:", name, user_name, password, verified, zipcode)

    # Mongo code for inserting data into our database
    mydb = myclient["foodpool"]
    mycol = mydb["users"]

    user_id = genID(8)

    while user_id in [i['user_id'] for i in mycol.find()]:
        user_id = genID(8)

    query = mycol.find( { 'user_name' : user_name })
    if (query.count() > 0):
        flash("Username taken")
        return redirect('/registerUser')

    user_record = {
        'user_id' : user_id,
        'name' : name,
        'user_name' : user_name,
        'password' : password,
        'verified' : verified,
        'zipcode' : zipcode,
    }

    zipcol = mydb["communities"]
    zipcodequery = zipcol.find( { "zipcode" : zipcode} )

    # if (zipcodequery.count() == 0):
        # flash("Community doesn't exist in our database! Contact an admin to add your community!")
        # return redirect('/registerUser')

    mycol.insert_one(user_record)
    flash("Account created successfully!")
    return redirect('/loginUser')

class loginUserForm(FlaskForm):
    """Register user form."""
    user_name = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])
    submit = SubmitField('Login')

@app.route('/loginUser', methods=('GET', 'POST'))
def login():
    form = loginUserForm()
    return render_template('/loginUser.html', form = form)

@app.route('/loginUserSubmit', methods=('GET', 'POST'))
def login_submit():
    for key, value in request.form.items():
        # print("key: {0}, value: {1}".format(key, value))
        verified = "no"
        if (key == "user_name"):
            user_name = value
        elif (key == "password"):
            password = hashlib.md5(value.encode()).hexdigest()
    print("Found user info:", user_name)

    # Mongo code for inserting data into our database
    mydb = myclient["foodpool"]
    mycol = mydb["users"]
    query = mycol.find( { 'user_name' : user_name })

    # print(query[0]['password'])
    if (query.count() == 0):
        flash("Login failure")
        return redirect('/loginUser')
    else:
        session['user_id'] = query[0]['user_id']
        return redirect('/userHomepage')



# R(EAD) OPERATIONS
# Viweing the total # of posts in the community, viewing all of the posts in the
# community, viewing a user

@app.route('/allUsers')
def allUsers():
    mydb = myclient["foodpool"]
    mycol = mydb["users"]
    totalPosts = len([i for i in mycol.find()])

    if (totalPosts == 0):
        # print("\nNo users to show!")
        users = ["No users to show!"]
    else:
        # for i in mycol.find():
        #     print(i)
        users = mycol.find()
    return render_template('/allUsers.html', totalPosts = totalPosts, users = users)

@app.route('/viewAllPostings')
def view_postings():
    mydb = myclient["foodpool"]
    mycol = mydb["posts"]

    totalPosts = len([i for i in mycol.find()])

    if (totalPosts == 0):
        posts = ["No posts to show!"]
    else:
        posts = mycol.find()
    return render_template('/viewAllPostings.html', totalPosts = totalPosts, posts = posts)

class findUserPostings(FlaskForm):
    """Search user postings."""
    name = StringField('Name')
    food_zipcode = StringField('Enter zipcode here:', [DataRequired()])
    submit = SubmitField('Search postings!')

@app.route('/viewUserPostings', methods=('GET', 'POST'))
def view_user_postings():
    queryform = findUserPostings()
    # use our database
    mydb = myclient["foodpool"]
    # use the "users" collection
    postscol = mydb["posts"]
    postsquery = postscol.find()
    communities = []
    for post in postsquery:
        # print(post)
        if post['food_zipcode'] not in communities:
            communities.append(post['food_zipcode'])
    return render_template('/viewUserPostings.html', form = queryform, communities = communities)


@app.route('/viewUserPostingsSubmit', methods=('GET', 'POST'))
def view_user_postings_submit():
    # for key, value in request.form.items():
    #     print("key: {0}, value: {1}".format(key, value))
    #     if (key == "food_zipcode"):
    #         food_zipcode = value
    food_zipcode = request.form['ZipCodeDropDown']
    print(food_zipcode)

    # use our database
    mydb = myclient["foodpool"]
    # use the "users" collection
    postscol = mydb["posts"]
    # find the user with the user_name entered in the query
    postsquery = postscol.find( { "food_zipcode" : food_zipcode })

    totalPosts = postsquery.count()

    if (totalPosts == 0):
        posts = ["No postings to show!"]
    else:
        posts = postscol.find({ "food_zipcode" : food_zipcode })

    return render_template('/showUserPostings.html', posts = posts)


@app.route('/viewAccount', methods=('GET', 'POST'))
def view_account():
    # use our database
    mydb = myclient["foodpool"]
    # use the "users" collection
    userscol = mydb["users"]
    userquery = userscol.find( { "user_id" : session['user_id'] } )

    return render_template('viewAccount.html', user = userquery)

# U(PDATE) OPERATIONS
# Updating a users profile, updating the attributes of a community,
# updating a food item

class updateUser(FlaskForm):
    """Edit your profile here."""
    name = StringField('Enter your new name:')
    user_name = StringField('Enter your new username:')
    # ADMIN USE:
    # verified = BooleanField('Have you been verified?')
    zipcode = StringField('Enter your new zipcode:')
    password = PasswordField('Enter your new password here:')
    submit = SubmitField('Edit your profile!')

@app.route('/updateUser', methods=('GET', 'POST'))
def update_user():
    queryform = updateUser()
    return render_template('/updateUser.html', form = queryform)

@app.route('/updateUserSubmit', methods=('GET', 'POST'))
def update_user_submit():
    mydb = myclient["foodpool"]
    mycol = mydb["users"]

    for key, value in request.form.items():
        # print("key: {0}, value: {1}".format(key, value))
        if (key == "name"):
            name = value
        elif (key == "user_name"):
            user_name = value
        # ADMIN USE:
        # elif (key == "verified"):
        #     if (value == 'y'):
        #         verified = "yes"
        #     elif (value == 'n'):
        #         verified == "no"
        elif (key == "zipcode"):
            zipcode = value
        elif (key == "password"):
            password = hashlib.md5(value.encode()).hexdigest()

    queryDoc = { "user_id" : session['user_id'] }

    user = mycol.find( queryDoc )

    if (name != ""):
        updated = mycol.update_one( queryDoc,
         {'$set': { 'name' : name} } )

    if (user_name != ""):
        updated = mycol.update_one( queryDoc,
         {'$set': { 'user_name' : user_name} } )

    # ADMIN USE:
    # if (verified != ""):
        # newAttributes = { "$set" : { "verified" : verified } }
        # updated = mycol.update_one(user, { "verified" : verified })

    if (zipcode != ""):
        updated = mycol.update_one( queryDoc,
         {'$set': { 'zipcode' : zipcode} } )
    if (password != ""):
        updated = mycol.update_one( queryDoc,
         {'$set': { 'password' : password} } )

    return redirect('/userHomepage')

class updateFoodForm(FlaskForm):
    """Edit your food item here."""
    post_id = StringField('Enter the post id here:', [DataRequired()])
    food_name = StringField('New name of Food')
    food_description = TextAreaField('New description of your food!')
    food_price = StringField('Change price to:')
    food_zipcode = StringField('Change food zipcode:')
    submit = SubmitField('Edit your food item!')

@app.route('/updateFood', methods=('GET', 'POST'))
def update_food():
    queryform = updateFoodForm()
    return render_template('/updateFood.html', form = queryform)

@app.route('/updateFoodSubmit', methods=('GET', 'POST'))
def update_food_submit():
    mydb = myclient["foodpfool"]
    mycol = mydb["posts"]

    for key, value in request.form.items():
        # print("key: {0}, value: {1}".format(key, value))
        if (key == "post_id"):
            post_id = int(value)
        elif (key == "food_name"):
            food_name = value
        elif (key == "food_description"):
            food_description = value
        elif (key == "food_price"):
            food_price = value

    post = mycol.find( { "post_id" : post_id } )

    if (post.count() == 0):
        flash("No food item found")
        return redirect('/updateFood')


    elif (session['user_id'] == post[0]['user_id']):
        if (food_name != ""):
            updated = mycol.update_one({ "post_id" : post_id },
                 {'$set': { 'food_name' : food_name} } )

        if (food_description != ""):
            updated = mycol.update_one({ "post_id" : post_id },
                 {'$set': { 'food_description' : food_description} } )

        if (food_price != ""):
            updated = mycol.update_one({ "post_id" : post_id },
                 {'$set': { 'food_price' : food_price} } )
        if (food_zipcode != ""):
            updated = mycol.update_one({ "post_id" : post_id },
                 {'$set': { 'food_zipcode' : food_zipcode} } )
        return redirect('userHomepage')


# D(ELETE) OPERATIONS
# Delete a user, post, or community

class deleteUser(FlaskForm):
    """Delete your user here."""
    password = PasswordField('Enter your password here:', [DataRequired()])
    submit = SubmitField('Delete this user')

@app.route('/deleteUser', methods=('GET', 'POST'))
def delete_user():
    deleteForm = deleteUser()
    return render_template('/deleteUser.html', form = deleteForm)

@app.route('/deleteUserSubmit', methods=('GET', 'POST'))
def delete_user_submit():
    mydb = myclient["foodpool"]
    mycol = mydb["users"]

    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        if (key == "password"):
            password = hashlib.md5(value.encode()).hexdigest()

    user = mycol.find( { 'user_id' : session['user_id'] } )
    print(user.count())

    if (user[0]['password'] == password):
        mycol.delete_one({'user_id' : session['user_id'] } )
        flash("Account deleted successfully.")
        return redirect("/loginUser")
    else:
        flash("Account failed to delete. Please try again.")
        return redirect('/userHomepage')

class deletePost(FlaskForm):
    """Delete your post here."""
    post_id = StringField('Enter your post id here:', [DataRequired()])
    submit = SubmitField('Delete this post')

@app.route('/deletePost', methods=('GET', 'POST'))
def delete_post():
    deleteForm = deletePost()
    return render_template('/deletePost.html', form = deleteForm)

@app.route('/deletePostSubmit', methods=('GET', 'POST'))
def delete_post_submit():
    mydb = myclient["foodpool"]
    mycol = mydb["posts"]

    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        if (key == "post_id"):
            post_id = int(value)

    post = mycol.find( { "post_id" : post_id } )

    print(post.count())

    if (session['user_id'] == post[0]['user_id']):
        mycol.delete_one({"post_id" : post_id})
        ## bring user back to user homepage (userHomepage)
        deletedMessage = "Deleted post: " + str(post_id)
        flash(deletedMessage)
        return redirect('/userHomepage')
    else:
        flash("Error: Please login again")
        return redirect('/loginUser')

## ADMIN ONLY
class deleteCommunity(FlaskForm):
    """Delete a community."""
    zipcode = StringField('Enter the zipcode  here:', [DataRequired()])
    password = PasswordField('Enter your password here:', [DataRequired()])
    submit = SubmitField('Delete this community')

@app.route('/deleteCommunity', methods=('GET', 'POST'))
def delete_community():
    deleteForm = deleteCommunity()
    return render_template('/deleteCommunitySubmit.html', form = deleteForm)

@app.route('/deleteCommunitySubmit', methods=('GET', 'POST'))
def delete_community_submit():
    mydb = myclient["foodpool"]
    mycol = mydb["communities"]

    for key, value in request.form.items():
        print("key: {0}, value: {1}".format(key, value))
        if (key == "zipcode"):
            zipcode = value
    mycol.delete_one({"zipcode" : zipcode})


# HELPER FUNCTIONS
def genID(chars):
    idChars = ['0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    id = ''
    while len(id) != chars:
        id = id + random.choice(idChars)
    return id


# Main function
if __name__ == '__main__':
    app.run()
